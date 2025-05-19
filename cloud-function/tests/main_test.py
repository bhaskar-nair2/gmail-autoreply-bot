import json
import base64

import functions_framework
from main import process_new_email

global TESTING

TESTING = True

def main():
  print("Have you updated the History ID?")
  event_data = {'emailAddress': 'bhaskarnair.work@gmail.com', 'historyId': '16395'}
  encoded_data = base64.b64encode(json.dumps(event_data).encode()).decode()
  
  payload = functions_framework.CloudEvent(
  attributes={"type":"qq", "source":"qq"},
  data={
  "message": {
      "data": encoded_data,
        "messageId": "123456789012345",
        "message_id": "123456789012345",
        "publishTime": "2025-05-15T12:18:00.000Z",
        "publish_time": "2025-05-15T12:18:00.000Z"
    },
    "subscription": "projects/your-gcp-project-id/subscriptions/your-subscription-name"
    }
  )
  process_new_email(payload)

if __name__ == "__main__":
  main()
