# facility-autobadge

`facility-autobadge` creates a traffic light system for facility devices on your gitlab repo startpage. The traffic light system gets automatically updated based on the issues in the issues list. In that way, all users of the facility know the current status of the devices.

![autobadge example](resources/autobadge.png)

The created badges get sorted according the label colors, that allows the grouping of devices. 

Additionally, the badges show you when there was the last update (last comment) regarding the devices.

This project was developed in cooperation with our EM-Facility managers at the MPI-Dortmund **Daniel Prumbaum** and **Oliver Hofnagel**.

## Traffic system rules
The badges are automatically updated by using gitlab webhooks, according the following rules:

- For each label starting with the prefix "D:" it creates a badge with either the status "RUNNING","RUNNING | INFO", "LIMITED" or "DOWN".
- For a given device label ("D:XXX") it will set the status to:
    - "RUNNING" if there is no issue with the device label. The status label is green.
    - "RUNNING | INFO" Important information available. The status label is green, but the device name turns blue.
    - "LIMITED" if there is an issue with the device label. The status label is yellow.
    - "DOWN" if there is an issue with the device label and additionally it has the label "CRITICAL" assigned. The status label is red.


Issues with the label "logbook" will be ignored.

## Installation

To run the facility-autobadge, you need two things:
    - A running gitlab instance
    - A server where you can run the facility-badge server which is accessible by your gitlab instance.

 The server does not need any special hardware.  I assume that you already created a gitlab repository where the facility-badge system should working with.


### 1. Configure the script

On your facility-badge server do the following

1. Clone the repository using git and navigate into the repo directory

    ```bash
    gh repo clone MPI-Dortmund/facility-autobadge
    cd facility-autobadge
    ```

2. Create the conda environment `autobadge`

    ```bash
    conda create --name "autobadge" --file=config/conda_env.yml
    ```

    Check the path to your new conda environment with

    ```bash
    conda env list
    ```

    You will need the path later.

3. Create the configuration file

    Navigate to the `config` directory and make a copy of the sample configuration file named `badger.toml`:
    ```bash
    cd config
    cp badger_sample.toml badger.toml
    ```
    Now fill in your details into the badger.toml using a text editor of your choice.

### 2. Start the service

We run the badgeserver in the background using a `systemctl` service. If your server is running Ubuntu, you can set it up as follows:

1. Create a new service file `autobadge.service` in `/etc/systemd/system/` with the following content:

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

    Replace `YOUR_USER` and `YOUR_GROUP` with your user- and groupname respectively.

2. Start the new service with:

    ```
    sudo systemctl start autobadge.service
    ```

3. Check if it started without errors:

    ```
    sudo systemctl status autobadge.service
    ```
4. Enable the service so that it will be restarted in case of a reboot:

    ```
    sudo systemctl enable autobadge.service
    ```

### 3. Setup your gitlab repository

1. Create a label for each of your devices under `Project information -> Labels`. Make sure that each device label starts with the prefix "D:".

2. Create a label named `CRITICAL`

3. Create a label named `Information`

4. Create an access token under `Settings -> Access Tokens` token with the following permissions for Role 'OWNER':
    - API
    - READ_API

    Make sure that you copy the your access token. 

4. Setup the webhook under `Settings -> Webhook`

    - Set the URL to: `http://ip.to.your.server:8000/update/YOUR_ACCESS_TOKEN
    
        Replace YOUR_ACCESS_TOKEN with your access token ;-)

    - Activate `Mask portions of URL`
        - Set the field `Sensitive portion of URL` to YOUR_ACCESS_TOKEN and `How it looks in the UI` to "SECRET"
    - Activate the checkboxes:
        - Issue events
        - Confidential issues events
        - Comments
        - Confidential comments
    - Disable SSL Verification

    - Click "Add webhook"

5. Now you are basically ready! Test it by clicking on the `Test` dropdown list and selecting `Issue events`. If you go back to the start page of your repository, you should see all badges in green :-) 

You can now start create issues and it will update the traffic light system according the `Traffic system rules` mentioned above.