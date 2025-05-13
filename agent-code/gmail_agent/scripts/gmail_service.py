import os
import json
from dotenv import load_dotenv

from google.cloud import secretmanager
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

load_dotenv()

# --- Configuration (Set as Environment Variables in Cloud Function) ---
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT") 
SECRET_NAME_GMAIL_CREDS = os.environ.get("SECRET_NAME_GMAIL_CREDS")




class GmailService():
    def __init__(self):
        self.service = self.create_gmail_service()

    def create_gmail_service(self):
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
                    creds.refresh(Request()) 
                    print("Gmail credentials refreshed successfully.")
                else:
                    print("Error: Invalid or missing refresh token in stored Gmail credentials.")
                    raise ValueError("Invalid or missing refresh token for Gmail.")
            
            service = build("gmail", "v1", credentials=creds)
            print("Gmail API service built successfully.")
            return service
        except Exception as e:
            print(f"Error building Gmail service or refreshing token: {e}")
            raise ConnectionError(f"Could not build Gmail service: {e}")

# ! Global variable to hold the Gmail service instance
service_instance = None # Initialize as None

def initialize_service():
    global service_instance
    GMS = GmailService()
    service_instance = GMS.service
