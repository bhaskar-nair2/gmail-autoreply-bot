import os
from dotenv import load_dotenv

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.cloud import secretmanager


load_dotenv()

# ! If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.modify",
          "https://www.googleapis.com/auth/gmail.readonly",
          "https://www.googleapis.com/auth/gmail.compose",
          "https://www.googleapis.com/auth/gmail.send",
          "https://www.googleapis.com/auth/gmail.addons.current.message.action"
          ]
LABELS = ["INBOX", "Label_6682199651960682642"]
PUBSUB_TOPIC = "projects/vraie-3a692/topics/gmail_bot_messages"

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT") # Automatically set by Cloud Functions
SECRET_NAME_GMAIL_CREDS = os.environ.get("SECRET_NAME_GMAIL_CREDS") # Name of the secret in 


from google.cloud import secretmanager
import google_crc32c  # type: ignore


def add_secret_version() -> secretmanager.SecretVersion:
    """
    Add a new secret version to the given secret with the provided payload.
    """
    # Create the Secret Manager client.
    client = secretmanager.SecretManagerServiceClient()
    # Build the resource name of the parent secret.
    parent = client.secret_path(PROJECT_ID, SECRET_NAME_GMAIL_CREDS)
    # Convert the string payload into a bytes. This step can be omitted if you
    # pass in bytes instead of a str for the payload argument.
    
    with open("token.json", "rb") as f:
        payload_bytes = f.read()

    # Calculate payload checksum. Passing a checksum in add-version request
    # is optional.
    crc32c = google_crc32c.Checksum()
    crc32c.update(payload_bytes)

    # Add the secret version.
    response = client.add_secret_version(
        request={
            "parent": parent,
            "payload": {
                "data": payload_bytes,
                "data_crc32c": int(crc32c.hexdigest(), 16),
            },
        }
    )

    # Print the new secret version name.
    print(f"Added secret version: {response.name}")

def main():
  """Shows basic usage of the Gmail API.
  Lists the user's Gmail labels.
  """
  creds = None
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          "credentials.json", SCOPES
      )
      creds = flow.run_local_server(port=54842)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
      token.write(creds.to_json())
    # Add the secret version to Secret Manager
    add_secret_version()
      
  # Call gmail.user.watch to connect to cloud function
  try:
    # Call the Gmail API
    service = build("gmail", "v1", credentials=creds)
    service.users().watch(
        userId="me",
        body={
            "labelIds": LABELS,
            "topicName": PUBSUB_TOPIC,
        },
    ).execute()
    
    print("Watch request sent successfully.")

  except HttpError as error:
    # TODO(developer) - Handle errors from gmail API.
    print(f"An error occurred: {error}")
    
  try:
    # Call the Gmail API
    service = build("gmail", "v1", credentials=creds)
    results = service.users().labels().list(userId="me").execute()
    labels = results.get("labels", [])

    if not labels:
      print("No labels found.")
      return
    print("Labels:")
    for label in labels:
      print(f"Name: {label["name"]} ----- ID: {label["id"]}")

  except HttpError as error:
    # TODO(developer) - Handle errors from gmail API.
    print(f"An error occurred: {error}")


if __name__ == "__main__":
  main()
