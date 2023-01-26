import requests
import pprint
import re
from dataclasses import dataclass
from typing import List, Dict
import sys
import datetime
from fastapi import FastAPI
from enum import IntEnum
app = FastAPI()


api_url_labels = "https://gitlab.gwdg.de/api/v4/projects/28068/labels"
api_url_issues = "https://gitlab.gwdg.de/api/v4/projects/28068/issues?state=opened"
api_url_badges = "https://gitlab.gwdg.de/api/v4/projects/28068/badges"


class Status(IntEnum):
    RUNNING = 0
    LIMITED = 1
    DOWN = 2

status_color_map = {
    Status.RUNNING: "green",
    Status.LIMITED: "yellow",
    Status.DOWN: "red"
}

@dataclass
class DeviceStatus:
    status:Status
    latest_issue_link:str = None
    latest_issue_date:str = None
    group:int = None


def get_device_by_labels(lbls:List[str]) -> str:
    device = None
    for lbl in lbls:
        if str(lbl).startswith('D:'):
            device = lbl
    return device

def get_all_device_status(device_labels: List, issues: List[dict]) -> Dict[str, DeviceStatus]:
    device_labels = [r for r in device_labels if str(r['name']).startswith('D:')]
    label_colors = list(set([r['color'] for r in device_labels]))
    device_group_map = {l : label_colors.index(l) for l in label_colors}

    current_status: Dict[str,DeviceStatus] = {}
    for device in device_labels:
        current_status[device['name']] = DeviceStatus(status=Status.RUNNING, group=device_group_map[device['color']])

    for issue in issues:
        device = get_device_by_labels(issue['labels'])
        if not device:
            continue
        is_critical = 'CRITICAL' in issue['labels']
        
        issue_date = issue['updated_at'][:10]
        issue_link = issue['web_url']

        candidate_status = Status.LIMITED
        if is_critical:
            candidate_status = Status.DOWN
        print(device)
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
            current_status[device].status = candidate_status
            current_status[device].latest_issue_link = issue_link
            current_status[device].latest_issue_date = issue_date
    return current_status


def clean_devices_badges(all_badges, secret):
    for r_id, r in enumerate(all_badges):
        regex_found = re.findall('\/(D:.*?)\/', r['image_url'])# https://regex101.com/r/YQDd29/1

        if regex_found:
            id = r['id']
            url=api_url_badges+f"/{id}"
            resp = requests.delete(url, headers={'PRIVATE-TOKEN': secret})

        

def add_all_devices_badges(device_labels, issues, secret: str):

    status: Dict[str,DeviceStatus] = get_all_device_status(device_labels=device_labels,issues=issues)
    status = dict(sorted(status.items(), key=lambda x:x[1].group))
    # Create all batches
    for device in status:
        s=status[device].status
        date=""
        if status[device].latest_issue_date:
            date=f"-{status[device].latest_issue_date:}"
        link="https://gitlab.gwdg.de/mpi-dortmund/dept3/emfacility/-/boards"
        if status[device].latest_issue_link:
            link = status[device].latest_issue_link
        data = {
            "image_url": f"https://badgen.net/badge/{device}/{s.name}{date}/{status_color_map[s]}?icon=github",
            "link_url": link
        }
        res = requests.post(api_url_badges, headers={'PRIVATE-TOKEN': secret}, json=data)


def update_badges(secret: str):
    ## List all labels

    response = requests.get(api_url_labels, headers={'PRIVATE-TOKEN': secret})
    res = response.json()
    all_device_labels = res #[r['name'] for r in res if str(r['name']).startswith('D:')]

    ## List all issues 
    response = requests.get(api_url_issues, headers={'PRIVATE-TOKEN': secret})
    all_issues = response.json()

    response = requests.get(api_url_badges, headers={'PRIVATE-TOKEN': secret})
    all_badges = response.json()


    # Clean all device badges
    print("Clean")
    clean_devices_badges(all_badges, secret)
    print("Fill")
    add_all_devices_badges(all_device_labels, all_issues, secret)

@app.post("/update/{secret}")
async def root(secret: str):
    print("Update")
    update_badges(secret)
    return {f"update done"}










