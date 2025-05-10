from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import os.path

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
  """Shows basic usage of the Gmail API.
  Initializes the Gmail service using credentials.
  """
  creds = None
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if os.path.exists('token.json'):
    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      try:
        creds.refresh(Request())
      except Exception as e:
        print(f"Failed to refresh token: {e}. Need to re-authenticate.")
        creds = None # Force re-authentication
    if not creds: # If refresh failed or no token.json
       # Ensure 'credentials.json' is downloaded from Google Cloud Console
      if not os.path.exists('credentials.json'):
         print("Error: credentials.json not found. Please download it from Google Cloud Console.")
         return None
      flow = InstalledAppFlow.from_client_secrets_file(
        'credentials.json', SCOPES)
      # Run flow in console; for server apps, use different flow
      creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open('token.json', 'w') as token:
      token.write(creds.to_json())

  try:
    service = build('gmail', 'v1', credentials=creds)
    return service
  except HttpError as error:
    print(f'An error occurred building the service: {error}')
    return None
  except Exception as e:
    print(f'An unexpected error occurred: {e}')
    return None


def get_emails_from_history(service, start_history_id):
  """
  Retrieves messages added to the mailbox since the given startHistoryId.

  Args:
    service: Authorized Gmail API service instance.
    start_history_id: The starting history ID.

  Returns:
    A list of message objects added since the startHistoryId, or None if an error occurs.
  """
  try:
    history = service.users().history().list(
      userId='me',
      startHistoryId=start_history_id,
      historyTypes=['messageAdded'] # Focus on added messages
    ).execute()

    messages = []
    # History records are returned oldest first.
    changes = history.get('history', [])
    while 'nextPageToken' in history:
       page_token = history['nextPageToken']
       history = service.users().history().list(
         userId='me',
         startHistoryId=start_history_id,
         historyTypes=['messageAdded'],
         pageToken=page_token
       ).execute()
       changes.extend(history.get('history', []))


    for change in changes:
      added_messages = change.get('messagesAdded', [])
      for msg_info in added_messages:
        msg = msg_info.get('message')
        if msg:
          # You might want to fetch the full message details here if needed
          # full_message = service.users().messages().get(userId='me', id=msg['id'], format='metadata').execute()
          # messages.append(full_message)
          messages.append(msg) # Add basic message info (id, threadId)

    return messages

  except HttpError as error:
    print(f'An error occurred: {error}')
    # Handle specific errors like invalid startHistoryId if needed
    if error.resp.status == 404:
       print(f"History ID {start_history_id} not found.")
    return None
  except Exception as e:
    print(f'An unexpected error occurred during history retrieval: {e}')
    return None

if __name__ == '__main__':
  # Replace with the actual startHistoryId you want to query from
  # You typically get this from a previous API call or a push notification
  start_history_id = 'YOUR_START_HISTORY_ID' # <<< --- REPLACE THIS

  if start_history_id == 'YOUR_START_HISTORY_ID':
    print("Please replace 'YOUR_START_HISTORY_ID' with an actual history ID.")
  else:
    gmail_service = get_gmail_service()
    if gmail_service:
      print(f"Fetching emails added since history ID: {start_history_id}")
      new_emails = get_emails_from_history(gmail_service, start_history_id)

      if new_emails is not None:
        if new_emails:
          print(f"\nFound {len(new_emails)} new messages:")
          for email in new_emails:
            print(f"  Message ID: {email.get('id')}, Thread ID: {email.get('threadId')}")
            # To get more details (Subject, From, etc.), you'd need another API call:
            # msg_detail = gmail_service.users().messages().get(userId='me', id=email.get('id'), format='metadata').execute()
            # headers = msg_detail.get('payload', {}).get('headers', [])
            # subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'N/A')
            # print(f"    Subject: {subject}")
        else:
          print("No new messages found since the specified history ID.")
      else:
        print("Failed to retrieve email history.")
    else:
      print("Failed to initialize Gmail service.")
