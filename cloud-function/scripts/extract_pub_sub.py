import base64
import json

import functions_framework

def decode_pub_sub(cloud_event: functions_framework.CloudEvent):
    """
    Decode the Pub/Sub message from Gmail watch.
    """
    try:
        pubsub_message_str = base64.b64decode(cloud_event.data["message"]["data"]).decode("utf-8")
        pubsub_data = json.loads(pubsub_message_str)
        notified_email_address = pubsub_data.get("emailAddress")
        history_id = pubsub_data.get("historyId")
        print(f"Pub/Sub Notification for: {notified_email_address}, History ID: {history_id}")
        return notified_email_address, history_id
    except Exception as e:
        print(f"Error decoding Pub/Sub message: {e}")
        return print(f"Bad Request: Invalid Pub/Sub message format: {e}", 400) # Acknowledge to prevent retries for bad format  
