# main.py
from dotenv import load_dotenv
# Call before importing any other modules to ensure env vars are loaded
load_dotenv()

# Ext Deps
import functions_framework

# Services
from services.vertex_ai_service import create_agent_engine_client
from services.gmail_service import GmailService

# Scripts
from scripts.get_mails import get_emails_from_history, get_email_details
from scripts.send_mails import send_mail
from scripts.extract_pub_sub import decode_pub_sub
from scripts.get_agent_session import get_agent_session
from scripts.call_agent import make_agent_call
from scripts.history_id_manager import get_last_processed_history_id, update_last_processed_history_id
from scripts.change_mail_labels import mark_as_read


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
    print(f"\n-----Received Cloud Event-----\n")
    
    try:
        # Decode pub/sub message
        notified_email_address, notified_history_id = decode_pub_sub(cloud_event)
        
        last_processed_history_id = get_last_processed_history_id(notified_email_address)
        if not last_processed_history_id:
            last_processed_history_id = notified_history_id
        # Fetch mails using historyId
        new_emails = get_emails_from_history(gmail_service, history_id = last_processed_history_id)
        if len(new_emails) == 0:
            print("No new mails to process!!")
        # Loop through messages in the history
        for email_content in new_emails:
            # Fetch full email content
            email_data = get_email_details(email_content)
            thread_id = f"{email_data['thread_id']}"
            message_id = f"{email_data['message_id']}"
            # Find an existing agent session for the email's threadId or create one
            agent_session = get_agent_session(agent_engine_client, thread_id)
            
            # Send message body and other info to the agent using the session
            # ? Agent can use it's own tools to fetch more data if needed
            agent_response = make_agent_call(
                agent_engine_client, 
                thread_id, 
                agent_session.get("id"), 
                email_data
                )
            
            # Use send_mail to send the reply
            send_mail(
                gmail_service,
                to_email= email_data.get("from"), # !
                from_email= notified_email_address,
                subject= email_data.get("subject"), # ? to reply to same thread
                content= agent_response
            )
            
            # Mark email as read
            mark_as_read(gmail_service, notified_email_address, message_id)
        
        # Update History ID in Firestore
        update_last_processed_history_id(notified_email_address, notified_history_id)
    except Exception as e:
        print(f"-----Error processing Event: {e}-----")
        return print("Error processing Event.", 500)
    else:
        return print("-----Event processed successfully-----", 200)

