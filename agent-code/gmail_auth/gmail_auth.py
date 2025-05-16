import os
from dotenv import load_dotenv

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.cloud import secretmanager
import google_crc32c  # type: ignore

load_dotenv()

# ! If modifying these scopes, delete the file token.json.
SCOPES = [
          "https://www.googleapis.com/auth/gmail.readonly",
          "https://www.googleapis.com/auth/gmail.compose",
          "https://www.googleapis.com/auth/gmail.send",
          "https://www.googleapis.com/auth/gmail.addons.current.message.action"
          ]
# Automatically set by Cloud Functions
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT") 
# Name of the secret in 
SECRET_NAME_GMAIL_CREDS = os.environ.get("SECRET_NAME_GMAIL_CREDS") 

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

def create_token_file():
  """
  Creates a token.json file with the user's access and refresh tokens.
  This file is created automatically when the authorization flow completes for
  the first time.
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
      
def refresh_gmail_token():
  """
  Creates a token.json file with the user's access and refresh tokens.
  Then saves it in the GCP Secret Manager.
  """
  print("--------Refreshing Gmail token----------")
  create_token_file()
  add_secret_version()
  print("--------Token Refreshed----------")
  

