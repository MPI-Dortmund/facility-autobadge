import datetime
import logging
import os
import re
import urllib.parse
from dataclasses import dataclass
from enum import IntEnum
from typing import List, Dict

import requests

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from fastapi import FastAPI

logging.basicConfig(format='%(asctime)s - %(message)s', filename='webhook-server.log', encoding='utf-8', level=logging.DEBUG)

app = FastAPI()

PAGE_LIMIT=200

# Project URL
config: Dict


class Status(IntEnum):
    RUNNING = 0
    INFO = 1
    LIMITED = 2
    DOWN = 3

status_color_map = {
    Status.RUNNING: "green?list=|",
    Status.INFO: "green?labelColor=blue&list=|",
    Status.LIMITED: "yellow?list=|",
    Status.DOWN: "red?list=|"
}

status_name_map = {
    Status.RUNNING: "RUNNING",
    Status.INFO: "RUNNING,INFO",
    Status.LIMITED: "LIMITED",
    Status.DOWN: "DOWN"
}

@dataclass
class DeviceStatus:
    '''
    Represent a device and its status
    '''
    status:Status
    latest_issue_link:str = None
    latest_issue_date:str = None
    days_since_update:int = None
    group:int = None


def get_device_by_labels(lbls:List[str]) -> str:
    '''
    Find the devices label. Return none if no label is a device label (starts with 'D:')
    '''
    device = None
    for lbl in lbls:
        if str(lbl).startswith('D:'):
            device = lbl
    return device

def get_all_device_status(device_labels: List, issues: List[dict]) -> Dict[str, DeviceStatus]:
    device_labels = [r for r in device_labels if str(r['name']).startswith('D:')]
    label_colors = list(set([r['color'] for r in device_labels]))
    label_colors.sort()
    device_group_map = {l : label_colors.index(l) for l in label_colors}

    current_status: Dict[str,DeviceStatus] = {}
    for device in device_labels:
        current_status[device['name']] = DeviceStatus(status=Status.RUNNING, group=device_group_map[device['color']])

    for issue in issues:
        device = get_device_by_labels(issue['labels'])
        if not device:
            # in that case, the issue does not belong to devices therefore no device needs to be updated
            continue

        is_critical = 'CRITICAL' in issue['labels']
        is_info = 'Information' in issue['labels']
        is_logbook = 'Logbook' in issue['labels']

        if is_logbook:
            # If its a logbook entry, it has no influence on the status of a device
            continue
        
        issue_date = issue['updated_at'][:10]
        issue_days_since_update = (datetime.datetime.today()-datetime.datetime.strptime(issue_date,'%Y-%m-%d')).days

        #issue_link = issue['web_url']
        issue_link = f"{config['repo']['project_url']}-/issues/?sort=updated_desc&state=opened&label_name[]={urllib.parse.quote_plus(device)}"

        candidate_status = Status.LIMITED
        if is_info:
            candidate_status = Status.INFO
        
        if is_critical:
            candidate_status = Status.DOWN
        
        update = False
        if current_status[device].status > candidate_status:
            # Ignore in case the current status is more severe
            continue
        elif current_status[device].status == candidate_status:
            #If severity is equal, update only when the issue is newer.
            current_issue_data = datetime.datetime.strptime(current_status[device].latest_issue_date,'%Y-%m-%d')
            candidate_issue_data = datetime.datetime.strptime(issue_date,'%Y-%m-%d')
            if candidate_issue_data > current_issue_data:
                update=True
        else:
            # The issue is more severe: Update!
            update=True
        
        if update:
            logging.info(f"Updating {device} - Set status to {candidate_status}")
            current_status[device].status = candidate_status
            current_status[device].latest_issue_link = issue_link
            current_status[device].latest_issue_date = issue_date
            current_status[device].days_since_update = issue_days_since_update
    return current_status


def clean_devices_badges(all_badges: List[Dict], secret: str):
    '''
    Delete all badges
    '''

    for r_id, r in enumerate(all_badges):
        regex_found = re.findall('\/(D:.*?)\/', r['image_url'])# https://regex101.com/r/YQDd29/1

        if regex_found:
            id = r['id']
            url=config['api']['badges']+f"/{id}"
            resp = requests.delete(url, headers={'PRIVATE-TOKEN': secret})
            logging.info(f"Delete {regex_found}. Response: {resp.status_code} {resp.reason}")

        

def add_all_devices_badges(device_labels: List[Dict], issues: List[Dict], secret: str):
    '''
    Create the badges and add them to GitLab
    '''

    status: Dict[str,DeviceStatus] = get_all_device_status(device_labels=device_labels,issues=issues)
    status = dict(sorted(status.items(), key=lambda x:x[1].group))
    # Create all batches
    for device in status:
        s=status[device].status
        date=""
        if status[device].latest_issue_date:
            date=f",Updated {status[device].days_since_update}d ago"
        link=f"{config['repo']['project_url']}-/boards"
        if status[device].latest_issue_link:
            link = status[device].latest_issue_link
        data = {
            "image_url": f"https://flat.badgen.net/badge/{device}/{status_name_map[s]}{date}/{status_color_map[s]}",
            "link_url": link
        }
        res = requests.post(config['api']['badges'], headers={'PRIVATE-TOKEN': secret}, json=data)
        logging.info(f"Add devices {device}. Reponse {res.status_code} {res.reason}")


def update_badges(secret: str):
    '''
        Updates all badges by first deleting all batches and the add them again with the most recent status.
    '''
    ## List all labels

    response = requests.get(config['api']['labels'], headers={'PRIVATE-TOKEN': secret})
    all_device_labels = response.json()

    ## List all issues 
    response = requests.get(config['api']['issues'], headers={'PRIVATE-TOKEN': secret})
    all_issues = response.json()
    
    ## List all badges
    response = requests.get(config['api']['badges']+f"?per_page={PAGE_LIMIT}", headers={'PRIVATE-TOKEN': secret})
    all_badges = response.json()
    
    ## Remove all badges
    logging.info("Delete all badges")
    clean_devices_badges(all_badges, secret)
    
    ## Add all badges
    logging.info("Create all badges with most recent status")
    add_all_devices_badges(all_device_labels, all_issues, secret)

@app.post("/update/{secret}")
async def root(secret: str):

    global config
    configpth = os.path.join(os.path.dirname(__file__), "../config/badger.toml")
    print(f"Load config: {configpth}")
    assert os.path.exists(configpth), "Can't find 'badger.toml' configuration file."

    with open(configpth, mode="rb") as fp:
        config = tomllib.load(fp)
    
    # Per page is necessay, as gitlab only returns those data that is visible on the page.
    config['api'] = {}
    config['api']['labels'] = f"{config['repo']['project_api_url']}labels?per_page={PAGE_LIMIT}"
    config['api']['issues'] = f"{config['repo']['project_api_url']}issues?state=opened&per_page={PAGE_LIMIT}"
    config['api']['badges'] = f"{config['repo']['project_api_url']}badges"

    print("Update")
    update_badges(secret)
    return {f"update done"}

