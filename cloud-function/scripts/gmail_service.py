import os
import json
from dotenv import load_dotenv

from google.cloud import secretmanager
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

load_dotenv()

# --- Configuration (Set as Environment Variables in Cloud Function) ---
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT") # Automatically set by Cloud Functions
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1") # Default if not set
TARGET_USER_EMAIL = os.environ.get("TARGET_USER_EMAIL") # The email alias being watched e.g., "your-alias@example.com"
SECRET_NAME_GMAIL_CREDS = os.environ.get("SECRET_NAME_GMAIL_CREDS") # Name of the secret in 

def get_gmail_service():
    """
    Authenticates and returns a Gmail API service object.
    Returns:
        service: Authorized Gmail API service instance.
    """
    creds = None
    if not PROJECT_ID or not SECRET_NAME_GMAIL_CREDS:
        print("Error: GCP_PROJECT or SECRET_NAME_GMAIL_CREDS env var not set.")
        raise ValueError("Missing project or secret name configuration for Gmail service.")

    try:
        client = secretmanager.SecretManagerServiceClient()
        secret_version_name = f"projects/{PROJECT_ID}/secrets/{SECRET_NAME_GMAIL_CREDS}/versions/latest"
        response = client.access_secret_version(name=secret_version_name)
        secret_payload = response.payload.data.decode("UTF-8")
        creds_info = json.loads(secret_payload)
        
        creds = Credentials.from_authorized_user_info(creds_info)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("Gmail credentials expired, attempting to refresh...")
                creds.refresh(Request()) # google.auth.transport.requests.Request
                print("Gmail credentials refreshed successfully.")
                # Note: In a long-running server, you'd persist the updated creds.
                # For a Cloud Function, this refreshed token is used for the current invocation.
            else:
                print("Error: Invalid or missing refresh token in stored Gmail credentials.")
                raise ValueError("Invalid or missing refresh token for Gmail.")
        
        service = build("gmail", "v1", credentials=creds)
        print("Gmail API service built successfully.")
        return service
    except Exception as e:
        print(f"Error building Gmail service or refreshing token: {e}")
        raise ConnectionError(f"Could not build Gmail service: {e}")
