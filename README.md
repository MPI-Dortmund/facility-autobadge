This is the repository for our gitlab webhooks. So far there is only autobadge. which creates badges according the following rules:


# facility-badge

Facility badge creates a traffic light system on your gitlab repo startpage. The traffic light system gets automatically updated based on the issues in the issues list. In that way, all users of the facility know the current status of the devices:

SHOW IMAGE HERE

## Traffic system rules
The badges are automatically updated by using gitlab webhooks, according the following rules:

- For each label starting "D:" it creates a batch with either the status "RUNNING", "LIMITED" or "DOWN".
- For a given device label ("D:XXX") it will set the status to:
    - "RUNNING" if there is no issue with the device label
    - "RUNNING | INFO" Important information available.
    - "LIMITED" if there is an issue with the device label or
    - "DOWN" if there is an issue with the device label and additionally it has the label "CRITICAL" assigned
    
The created badges get sorted according the label colors, that allows the grouping of devices.

## Installation

The facility-badge server needs to reachable by your gitlab installation. It does not need any special hardware.  I assume that you already created a gitlab repository where the issue system should working on.


### Setup server

1. Clone the repository using git

2. Create the conda environment `autobadge`:
    ```bash
    conda create --name "autobadge" --file=conda_env.yml
    ```

    Check the path to your new conda environment with

    ```
    conda env list
    ```

    You will need the path later.

3. G



We keep the badgeserver running in the background by using a systemctl service. If you server is running ubuntu, you can setup it as follows:

1. Create a new service file `autobadge.service` in `/etc/systemd/system/` with the follwoing content:

    ```
    [Unit]
    Description=Autobadge gitlab server
    After=network.target

    [Service]
    User=YOUR_USER
    Group=YOUR_GROUP
    WorkingDirectory=/path/to/folder/which/contains/the/main/dot/py/
    ExecStart=/path/to/autobadge/conda/environment/bin/uvicorn main:app --host 0.0.0.0 --port 8000

    [Install]
    WantedBy=multi-user.target
    ```
2. Start the new service with:
    ```
    sudo systemctl start autobadge.service
    ```

3. Check if it started without errors:
    ```
    sudo systemctl status autobadge.service
    ```
4. Enable the service to get it restarted in case of a reboot:
    ```
    sudo systemctl enable autobadge.service
    ```



## Implementation details
The server that called by the webhook is running on https://cloud.gwdg.de/ and was setup by Thorsten Wagner.

The ip adress is 141.5.100.114 and it listens to port 8000.

Connect to it via:

```
cloud@141.5.100.114
```

Restart server with: 

```bash
sudo systemctl restart autobadge
```
