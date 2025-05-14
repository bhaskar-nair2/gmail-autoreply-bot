# main.py
from dotenv import load_dotenv
# Call before importing any other modules to ensure env vars are loaded
load_dotenv()

# Ext Deps
import functions_framework

# Services
from services.init_agent_eng import create_agent_engine_client
from services.gmail_service import GmailService

# Scripts
from scripts.get_mails import get_emails_from_history, get_email_details
# from scripts.send_mail import send_reply_email
from scripts.extract_pub_sub import decode_pub_sub
from scripts.get_agent_session import get_agent_session


# Get instance of Gmail Service and Agent Service
gmail_service = GmailService().service
agent_engine_client = create_agent_engine_client()

# Check if all services are working
if not agent_engine_client or not gmail_service:
    print("ERROR: Agent Engine or Gmail Service not initialized. Exiting.")
    raise SystemExit("Initialization error: Agent Engine or Gmail Service not ready.")


# --- Main Cloud Function Triggered by Pub/Sub ---
@functions_framework.cloud_event
def process_new_email(cloud_event : functions_framework.CloudEvent):
    print(f"Received event: {cloud_event}")
    
    # Decode pub/sub message
    notified_email_address, history_id = decode_pub_sub(cloud_event)
    
    # Fetch mails using historyId
    new_emails = get_emails_from_history(gmail_service, history_id)
    
    # Loop through messages in the history
    for email_content in new_emails:
        # Fetch full email content
        email_data = get_email_details(email_content)
        thread_id = f"{email_data['thread_id']}"
        # Find an existing agent session for the email's threadId or create one
        agent_session = get_agent_session(agent_engine_client, thread_id)
        
        # Send message body and other info to the agent using the session
        for event in agent_engine_client.stream_query(
        user_id=thread_id,
        session_id=agent_session.get("id"),
        message=f"{email_data}",
        ):
            print(event)

        # Agent can use it's own tools to fetch more data if needed
        # Get agent reply
        # Use send_mail to send the reply

    print(f"Successfully processed Pub/Sub event")
    return print("Email processed successfully.", 200)



if __name__ == "__main__":
    payload = functions_framework.CloudEvent(
    attributes={"type":"qq", "source":"qq"},
    data={
    "message": {
        "data": "eyJlbWFpbEFkZHJlc3MiOiAiYmhhc2thcm5haXIud29ya0BnbWFpbC5jb20iLCAiaGlzdG9yeUlkIjogIjEwNTc0In0=",
        "messageId": "123456789012345",
        "message_id": "123456789012345",
        "publishTime": "2025-05-15T12:18:00.000Z",
        "publish_time": "2025-05-15T12:18:00.000Z"
    },
    "subscription": "projects/your-gcp-project-id/subscriptions/your-subscription-name"
    })
    process_new_email(payload)
