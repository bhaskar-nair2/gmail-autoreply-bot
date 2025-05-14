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
        session_id=agent_session.id,
        message=email_data,
        ):
            print(event)

        # Agent can use it's own tools to fetch more data if needed
        # Get agent reply
        # Use send_mail to send the reply


    # # TODO: Fix this and add Alias support
    # if notified_email_address not in [TARGET_USER_EMAIL]:
    #     print(f"Ignoring notification for {notified_email_address} as it doesn't match TARGET_USER_EMAIL {TARGET_USER_EMAIL}.")
    #     return print("Notification for irrelevant user.", 200) # Acknowledge and exit

    # --- Fetch New Email(s) using historyId ---
    # IMPORTANT: A robust production solution needs to store the 'last_processed_history_id'
    # for TARGET_USER_EMAIL (e.g., in Firestore or Cloud Storage) and use
    # gmail_service.users().history().list(userId=TARGET_USER_EMAIL, startHistoryId=last_processed_history_id).execute()
    # to get all changes since the last processed event.
    # This simplified example will just try to get the latest message, which might miss emails
    # if multiple arrive quickly or if the function restarts.
    # new_emails = get_emails_from_history(gmail_service, history_id)
    
    # for email_content in new_emails:
    #     if email_content:
    #         # --- Call Agent Engine ---
    #         agent_reply_text = "Sorry, I encountered an issue and could not process your request fully." # Default
    #         try:
    #             # Create a unique session ID, perhaps based on message ID or thread ID for context
    #             # For simplicity, using a generic user_id here.
    #             # Consider using the sender's email hash or message_id as part of user_id for better session tracking.
    #             thread_id = f"{email_content['thread_id']}"
    #             message_id = f"{email_content['message_id_header']}"
    #             sender = f"{email_content['from']}"
    #             subject = f"{email_content['subject']}"
                
    #             agent_session = agent_engine_client.create_session(user_id=thread_id)
    #             agent_session_name = agent_session.session_name # Use the full resource name
    #             print(f"Created agent session: {agent_session_name}")

    #             print(f"Querying agent with email body for message {message_id}...")
    #             agent_response = call_ai_agent(email_content["body"], user_id=thread_id)
                
    #             agent_response = agent_engine_client.query(
    #                 user_id=thread_id,
    #                 session_name=agent_session_name,
    #                 message=email_content["body"],
    #             )
                
    #             print(f"Received agent response object for message {message_id}")
                
    #             current_agent_reply_text = ""
    #             if agent_response.content and agent_response.content.parts:
    #                 for part in agent_response.content.parts:
    #                     if part.text:
    #                         current_agent_reply_text += part.text + "\n"
                
    #             if current_agent_reply_text.strip():
    #                 agent_reply_text = current_agent_reply_text.strip()
    #             else:
    #                 print(f"Agent did not provide a text response for message {message_id}.")
    #                 # agent_reply_text remains the default error/apology

    #             print(f"Agent reply for message {message_id} (first 100 chars): {agent_reply_text[:100]}...")

    #         except Exception as e_agent:
    #             print(f"Error querying Agent Engine for message {message_id}: {e_agent}")
    #             # agent_reply_text will be the default error message

    #         # --- Send Reply Email ---
    #         print(f"Attempting to send reply for message {message_id}...")
    #         send_reply_email(gmail_service, TARGET_USER_EMAIL, email_content, agent_reply_text)
            
    #         # Mark email as read (or add a 'processed' label) to avoid reprocessing
    #         try:
    #             gmail_service.users().messages().modify(
    #                 userId=TARGET_USER_EMAIL,
    #                 id=message_id,
    #                 body={'removeLabelIds': ['UNREAD']}
    #             ).execute()
    #             print(f"Marked message {message_id} as read.")
    #         except Exception as e_modify:
    #             print(f"Error marking message {message_id} as read: {e_modify}")
            
    #     # After processing all messages in this history batch,
    #     # you would store the LATEST history_id from this batch
    #     # as the new 'last_processed_history_id' for the next invocation.
    #     # This is omitted for simplicity in this example.

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
