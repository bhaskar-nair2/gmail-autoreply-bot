# main.py
import base64
import json 
import os
from dotenv import load_dotenv

# Ext Deps
import functions_framework
import vertexai
from vertexai import agent_engines # Or vertexai.agent_engines for older SDK versions
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.cloud import secretmanager

load_dotenv()

# --- Configuration (Set as Environment Variables in Cloud Function) ---
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT") # Automatically set by Cloud Functions
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1") # Default if not set
AGENT_ENGINE_ID = os.environ.get("AGENT_ENGINE_ID") # Full resource name of your Reasoning Engine
TARGET_USER_EMAIL = os.environ.get("TARGET_USER_EMAIL") # The email alias being watched e.g., "your-alias@example.com"
SECRET_NAME_GMAIL_CREDS = os.environ.get("SECRET_NAME_GMAIL_CREDS") # Name of the secret in Secret Manager
# Example: "gmail-oauth-credentials"
# The secret should contain the JSON:
# {
#   "client_id": "YOUR_CLIENT_ID",
#   "client_secret": "YOUR_CLIENT_SECRET",
#   "refresh_token": "YOUR_REFRESH_TOKEN",
#   "token_uri": "https://oauth2.googleapis.com/token",
#   "scopes": ["https://www.googleapis.com/auth/gmail.modify"]
# }

# --- Initialize Vertex AI (outside handler for reuse if possible) ---
# This might cause issues if the function scales down to zero and init is slow.
# Consider initializing within the handler if cold starts become problematic,
# but be mindful of re-initialization overhead.
try:
    if PROJECT_ID and LOCATION and AGENT_ENGINE_ID:
        print(f"Initializing Vertex AI for project {PROJECT_ID} in {LOCATION}...")
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        agent_engine_client = agent_engines.AgentEngine(AGENT_ENGINE_ID)
        print(f"Initialized Vertex AI and Agent Engine client for: {AGENT_ENGINE_ID}")
    else:
        print("ERROR: Missing one or more environment variables for Vertex AI init: GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION, AGENT_ENGINE_ID")
        agent_engine_client = None
except Exception as e:
    print(f"FATAL: Could not initialize Vertex AI or Agent Engine: {e}")
    agent_engine_client = None

# --- Helper Function to Get Gmail Service ---
def get_gmail_service():
    """Authenticates and returns a Gmail API service object."""
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

# --- Helper function to extract relevant email parts ---
def get_email_details(message_resource):
    """Extracts sender, subject, and plain text body from message payload."""
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

# --- Helper function to send reply ---
def send_reply_email(service, user_id, original_email_data, reply_body_text):
    """Sends a reply email."""
    try:
        if not original_email_data.get("from"):
            print("Error: Cannot reply, original sender not found.")
            return False

        # Ensure reply_body_text is not None
        reply_body_text = reply_body_text or "No response content."

        message = f"To: {original_email_data['from']}\n"
        message += f"Subject: Re: {original_email_data['subject']}\n"
        if original_email_data.get("message_id_header"):
            message += f"In-Reply-To: {original_email_data['message_id_header']}\n"
            message += f"References: {original_email_data['message_id_header']}\n"
        message += "Content-Type: text/plain; charset=utf-8\n\n"
        message += reply_body_text

        encoded_message = base64.urlsafe_b64encode(message.encode('utf-8')).decode('utf-8')
        
        send_request_body = {'raw': encoded_message}
        if original_email_data.get("thread_id"):
             send_request_body['threadId'] = original_email_data["thread_id"]

        sent_message = service.users().messages().send(userId=user_id, body=send_request_body).execute()
        print(f"Reply email sent. Message ID: {sent_message['id']}")
        return True

    except HttpError as error:
        print(f"An API error occurred sending reply: {error}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred sending reply: {e}")
        return False

# --- Main Cloud Function Triggered by Pub/Sub ---
@functions_framework.cloud_event
def process_new_email(cloud_event : functions_framework.CloudEvent):
    global agent_engine_client # Use the globally initialized agent engine client

    print(f"Received event: {cloud_event}")

    # Check for required environment variables
    if not all([PROJECT_ID, LOCATION, AGENT_ENGINE_ID, TARGET_USER_EMAIL, SECRET_NAME_GMAIL_CREDS]):
        print("ERROR: Missing one or more critical environment variables. Exiting.")
        # Consider raising an exception to force a retry if appropriate
        return print("Configuration error: Missing environment variables.", 500)


    if not agent_engine_client:
        print("Agent Engine client not initialized, cannot process. This might indicate an issue during startup.")
        # Depending on retry strategy, you might want to raise an exception here
        return print("Internal Server Error: Agent Engine not ready.", 503)


    # Decode Pub/Sub message from Gmail watch
    try:
        pubsub_message_str = base64.b64decode(cloud_event.data["message"]["data"]).decode("utf-8")
        pubsub_data = json.loads(pubsub_message_str)
        notified_email_address = pubsub_data.get("emailAddress")
        history_id = pubsub_data.get("historyId")
        print(f"Notification for: {notified_email_address}, History ID: {history_id}")
    except Exception as e:
        print(f"Error decoding Pub/Sub message: {e}")
        return print(f"Bad Request: Invalid Pub/Sub message format: {e}", 400) # Acknowledge to prevent retries for bad format

    # TODO: Fix this and add Alias support
    if notified_email_address != TARGET_USER_EMAIL:
        print(f"Ignoring notification for {notified_email_address} as it doesn't match TARGET_USER_EMAIL {TARGET_USER_EMAIL}.")
        return print("Notification for irrelevant user.", 200) # Acknowledge and exit

    gmail_service = None
    try:
        gmail_service = get_gmail_service()
    except Exception as e: # Catch errors from get_gmail_service
        print(f"Failed to initialize Gmail service: {e}")
        # Decide on retry. If it's a config error (like bad secret), retrying won't help.
        # If it's a transient network issue, retry might be okay.
        # For now, exit to prevent infinite loops on bad config.
        return print(f"Internal Server Error: Could not connect to Gmail: {e}", 503)


    # --- Fetch New Email(s) using historyId ---
    # IMPORTANT: A robust production solution needs to store the 'last_processed_history_id'
    # for TARGET_USER_EMAIL (e.g., in Firestore or Cloud Storage) and use
    # gmail_service.users().history().list(userId=TARGET_USER_EMAIL, startHistoryId=last_processed_history_id).execute()
    # to get all changes since the last processed event.
    # This simplified example will just try to get the latest message, which might miss emails
    # if multiple arrive quickly or if the function restarts.
    try:
        print(f"Fetching history for historyId: {history_id} (Note: using simplified message retrieval)")
        history_response = gmail_service.users().history().list(
            userId=TARGET_USER_EMAIL,
            startHistoryId=history_id,
            historyTypes=['messageAdded'] # Only interested in new messages
        ).execute()

        changes = history_response["history"]
        if not changes:
            print(f"No new message history found for historyId {history_id}. This might happen if changes were not 'messageAdded' or already processed.")
            return print("No new messages to process for this history event.", 200)

        # Process messages from history
        # Typically, history entries are ordered oldest to newest.
        for history_entry in changes:
            added_messages = history_entry["messagesAdded"]
            for added_msg_info in added_messages:
                message_id = added_msg_info['message']['id']
                # Ensure this message is INBOX and UNREAD (or matches your alias's label)
                # to avoid processing sent mail, drafts, or already handled mail.
                # The watch itself can be filtered by labelIds, but an extra check here is good.
                message_resource = gmail_service.users().messages().get(
                    userId=TARGET_USER_EMAIL, id=message_id, format='full'
                ).execute()

                # Check if the message is unread and in inbox (basic filter)
                label_ids = message_resource.get('labelIds', [])
                if 'UNREAD' not in label_ids or 'INBOX' not in label_ids: # Adjust if your alias uses a different primary label
                    print(f"Skipping message {message_id} as it's not UNREAD/INBOX (Labels: {label_ids}).")
                    continue

                print(f"Processing new message ID: {message_id}")
                email_content = get_email_details(message_resource)

                if not email_content.get("body"):
                    print(f"Could not extract body for message {message_id}. Skipping.")
                    continue # Or send a generic error reply

                print(f"Email body for agent (first 100 chars): {email_content['body'][:100]}...")

                # --- Call Agent Engine ---
                agent_reply_text = "Sorry, I encountered an issue and could not process your request fully." # Default
                try:
                    # Create a unique session ID, perhaps based on message ID or thread ID for context
                    # For simplicity, using a generic user_id here.
                    # Consider using the sender's email hash or message_id as part of user_id for better session tracking.
                    function_user_id = f"gmail_function_user_{TARGET_USER_EMAIL[:TARGET_USER_EMAIL.find('@')]}" 
                    
                    agent_session = agent_engine_client.create_session(user_id=function_user_id)
                    agent_session_name = agent_session.session_name # Use the full resource name
                    print(f"Created agent session: {agent_session_name}")

                    print(f"Querying agent with email body for message {message_id}...")
                    agent_response = agent_engine_client.query(
                        user_id=function_user_id,
                        session_name=agent_session_name,
                        message=email_content["body"],
                    )
                    
                    print(f"Received agent response object for message {message_id}")
                    
                    current_agent_reply_text = ""
                    if agent_response.content and agent_response.content.parts:
                        for part in agent_response.content.parts:
                            if part.text:
                                current_agent_reply_text += part.text + "\n"
                    
                    if current_agent_reply_text.strip():
                        agent_reply_text = current_agent_reply_text.strip()
                    else:
                        print(f"Agent did not provide a text response for message {message_id}.")
                        # agent_reply_text remains the default error/apology

                    print(f"Agent reply for message {message_id} (first 100 chars): {agent_reply_text[:100]}...")

                except Exception as e_agent:
                    print(f"Error querying Agent Engine for message {message_id}: {e_agent}")
                    # agent_reply_text will be the default error message

                # --- Send Reply Email ---
                print(f"Attempting to send reply for message {message_id}...")
                send_reply_email(gmail_service, TARGET_USER_EMAIL, email_content, agent_reply_text)
                
                # Mark email as read (or add a 'processed' label) to avoid reprocessing
                try:
                    gmail_service.users().messages().modify(
                        userId=TARGET_USER_EMAIL,
                        id=message_id,
                        body={'removeLabelIds': ['UNREAD']}
                    ).execute()
                    print(f"Marked message {message_id} as read.")
                except Exception as e_modify:
                    print(f"Error marking message {message_id} as read: {e_modify}")
            
            # After processing all messages in this history batch,
            # you would store the LATEST history_id from this batch
            # as the new 'last_processed_history_id' for the next invocation.
            # This is omitted for simplicity in this example.

    except HttpError as error:
        print(f"An API error occurred processing history: {error}")
        # Depending on the error, you might want to NACK to retry
        return print(f"Gmail API Error during history processing: {error.resp.status} - {error._get_reason()}", 500)
    except Exception as e:
        print(f"An unexpected error occurred during email processing: {e}")
        return print(f"Unexpected error during email processing: {e}", 500)

    print(f"Successfully processed Pub/Sub event {cloud_event.id}")
    return print("Email processed successfully.", 200)

