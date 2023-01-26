# gitlab_webhooks

This is the repository for our gitlab webhooks. So far there is only autobadge, which creates badges according the following rules:

- For each label starting "D:" it creates a batch with either the status "RUNNING", "LIMITED" or "DOWN".
- For a given device label ("D:XXX") it will set the status to:
    - "RUNNING" if there is no issue with the device label
    - "LIMITED" if there is an issue with the device label or
    - "DOWN" if there is an issue with the device label and additionally it has the label "CRITICAL" assigned

The server that called by the webhook is running on https://cloud.gwdg.de/ and was setup by Thorsten Wagner.

The ip adress is 141.5.100.114 and it listens to port 8000.

