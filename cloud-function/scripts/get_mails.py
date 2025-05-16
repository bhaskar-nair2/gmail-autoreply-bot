import base64

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_emails_from_history(service,*, history_id) -> list:
  """
  Retrieves messages added to the mailbox since the given startHistoryId.

  Args:
    service: Authorized Gmail API service instance.
    history_id: The starting history ID.

  Returns:
    A list of message objects added since the startHistoryId, or None if an error occurs.
  """
  print("Getting history from gmail")
  try:
    history = service.users().history().list(
      userId='me',
      startHistoryId=history_id,
      historyTypes=['messageAdded'] # Focus on added messages
    ).execute()

    messages = []
    # History records are returned oldest first.
    changes = history.get('history', [])
    while 'nextPageToken' in history:
       page_token = history['nextPageToken']
       history = service.users().history().list(
         userId='me',
         startHistoryId=history_id,
         historyTypes=['messageAdded'],
         pageToken=page_token
       ).execute()
       changes.extend(history.get('history', []))
    
    for change in changes:
      added_messages = change.get('messages', [])
      for msg in added_messages:
        if msg:
          # Fetch the full message details here
          full_message = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
          # Extract relevant details
          messages.append(full_message) 
    print(f"{len(messages)} New messages found")
    return messages

  except HttpError as error:
    print(f'An error occurred: {error}')
    # Handle specific errors like invalid startHistoryId if needed
    if error.resp.status == 404:
       print(f"History ID {history_id} not found.")
    return None
  except Exception as e:
    print(f'An unexpected error occurred during history retrieval: {e}')
    return None


# --- Helper function to extract relevant email parts ---
def get_email_details(message_resource):
    """
    Extracts sender, subject, and plain text body from message payload.
    """
    
    email_data = {"from": None, "subject": None, "body": None, "thread_id": None, "message_id_header": None}
    try:
        payload = message_resource.get("payload", {})
        headers = payload.get("headers", [])
        
        email_data["from"] = next((h["value"] for h in headers if h["name"].lower() == "from"), None)
        email_data["subject"] = next((h["value"] for h in headers if h["name"].lower() == "subject"), "No Subject")
        email_data["message_id_header"] = next((h["value"] for h in headers if h["name"].lower() == "message-id"), None)
        email_data["thread_id"] = message_resource.get("threadId")

        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    body_data = part['body'].get('data')
                    if body_data:
                        email_data["body"] = base64.urlsafe_b64decode(body_data).decode('utf-8')
                        break # Found plain text, stop
        elif payload.get('mimeType') == 'text/plain':
             body_data = payload['body'].get('data')
             if body_data:
                 email_data["body"] = base64.urlsafe_b64decode(body_data).decode('utf-8')
        
        if not email_data["body"]:
             # Fallback or get snippet if no plain text body
             email_data["body"] = message_resource.get("snippet", "Could not extract body.")
             print("Could not find plain text body part, using snippet.")

        return email_data
    except Exception as e:
        print(f"Error parsing email details: {e}")
        return email_data # Return partially filled data

# For testing purposes, you can run this script directly.
# if __name__ == '__main__':
#   # Replace with the actual startHistoryId you want to query from
#   # You typically get this from a previous API call or a push notification
#   start_history_id = '6212' # <<< --- REPLACE THIS

#   gmail_service = get_gmail_service()
#   if gmail_service:
#     print(f"Fetching emails added since history ID: {start_history_id}")
#     new_emails = get_emails_from_history(gmail_service, start_history_id)

#     if new_emails is not None:
#       if new_emails:
#         print(f"\nFound {len(new_emails)} new messages:")
#         for email in new_emails:
#           print(f"  Message ID: {email.get('id')}, Data {get_email_details(email)}")
#           # To get more details (Subject, From, etc.), you'd need another API call:
#           # msg_detail = gmail_service.users().messages().get(userId='me', id=email.get('id'), format='metadata').execute()
#           # headers = msg_detail.get('payload', {}).get('headers', [])
#           # subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'N/A')
#           # print(f"    Subject: {subject}")
#       else:
#         print("No new messages found since the specified history ID.")
#     else:
#       print("Failed to retrieve email history.")
#   else:
#     print("Failed to initialize Gmail service.")
