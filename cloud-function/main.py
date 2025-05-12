# main.py
import base64
import json 
import os
from dotenv import load_dotenv

# Ext Deps
import functions_framework
import vertexai
from vertexai import agent_engines # Or vertexai.agent_engines for older SDK versions
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Scripts
from scripts.gmail_service import get_gmail_service
from scripts.get_mails import get_emails_from_history
from scripts.send_mail import send_reply_email

load_dotenv()

# --- Configuration (Set as Environment Variables in Cloud Function) ---
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT") # Automatically set by Cloud Functions
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1") # Default if not set
AGENT_ENGINE_ID = os.environ.get("AGENT_ENGINE_ID") # Full resource name of your Reasoning Engine
TARGET_USER_EMAIL = os.environ.get("TARGET_USER_EMAIL") # The email alias being watched e.g., "your-alias@example.com"
SECRET_NAME_GMAIL_CREDS = os.environ.get("SECRET_NAME_GMAIL_CREDS") # Name of the secret in Secret Manager

# --- Initialize Vertex AI (outside handler for reuse if possible) ---
# This might cause issues if the function scales down to zero and init is slow.
# Consider initializing within the handler if cold starts become problematic,
# but be mindful of re-initialization overhead.
try:
    if PROJECT_ID and LOCATION and AGENT_ENGINE_ID:
        pass
        # print(f"Initializing Vertex AI for project {PROJECT_ID} in {LOCATION}...")
        # vertexai.init(project=PROJECT_ID, location=LOCATION)
        # agent_engine_client = agent_engines.get(AGENT_ENGINE_ID)
        # print(f"Initialized Vertex AI and Agent Engine client for: {AGENT_ENGINE_ID}")
    else:
        print("ERROR: Missing one or more environment variables for Vertex AI init: GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION, AGENT_ENGINE_ID")
        agent_engine_client = None
except Exception as e:
    print(f"FATAL: Could not initialize Vertex AI or Agent Engine: {e}")
    agent_engine_client = None

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
        print(f"Pub/Sub Data: {pubsub_data}")
        print(f"Notification for: {notified_email_address}, History ID: {history_id}")
    except Exception as e:
        print(f"Error decoding Pub/Sub message: {e}")
        return print(f"Bad Request: Invalid Pub/Sub message format: {e}", 400) # Acknowledge to prevent retries for bad format

    # TODO: Fix this and add Alias support
    if notified_email_address not in [TARGET_USER_EMAIL]:
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
    new_emails = get_emails_from_history(gmail_service, history_id)
    
    for email_content in new_emails:
        if email_content:
            # --- Call Agent Engine ---
            agent_reply_text = "Sorry, I encountered an issue and could not process your request fully." # Default
            try:
                # Create a unique session ID, perhaps based on message ID or thread ID for context
                # For simplicity, using a generic user_id here.
                # Consider using the sender's email hash or message_id as part of user_id for better session tracking.
                thread_id = f"{email_content['thread_id']}"
                message_id = f"{email_content['message_id_header']}"
                sender = f"{email_content['from']}"
                subject = f"{email_content['subject']}"
                
                agent_session = agent_engine_client.create_session(user_id=thread_id)
                agent_session_name = agent_session.session_name # Use the full resource name
                print(f"Created agent session: {agent_session_name}")

                print(f"Querying agent with email body for message {message_id}...")
                agent_response = call_ai_agent(email_content["body"], user_id=thread_id)
                
                agent_response = agent_engine_client.query(
                    user_id=thread_id,
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

    print(f"Successfully processed Pub/Sub event {cloud_event.id}")
    return print("Email processed successfully.", 200)

