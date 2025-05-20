# main.py
from dotenv import load_dotenv
# Call before importing any other modules to ensure env vars are loaded
load_dotenv()

# Ext Deps
import functions_framework
from flask import make_response # For HTTP responses

# Services
# Assuming these service initializations are robust and handle their own credential loading
from services.vertex_ai_service import create_agent_engine_client
from services.gmail_service import GmailService
from services.firestore_service import firestore_db_client # Assuming this is your initialized firestore client instance

# Scripts
from scripts.get_mails import get_emails_from_history, get_email_details
from scripts.send_mails import send_mail 
from scripts.change_mail_labels import mark_as_read as mark_email_as_read_in_gmail
# decode_pub_sub is no longer needed for an HTTP trigger
from scripts.get_agent_session import get_agent_session # Manages agent session creation/retrieval
from scripts.call_agent import make_agent_call
from scripts.history_id_manager import get_last_processed_history_id, update_last_processed_history_id, create_baseline_history_id

import os
import sys
import json # For potential request body parsing if needed

# --- Configuration (from Environment Variables) ---
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
AGENT_ENGINE_ID = os.environ.get("AGENT_ENGINE_ID")
TARGET_USER_EMAIL = os.environ.get("TARGET_USER_EMAIL") # Crucial for polling
SECRET_NAME_GMAIL_CREDS = os.environ.get("SECRET_NAME_GMAIL_CREDS") # Still needed by GmailService
FIRESTORE_HISTORY_COLLECTION = os.environ.get("FIRESTORE_HISTORY_COLLECTION", "gmailUserHistoryState")


# --- Initialize Global Clients ---
# These are initialized when the Cloud Function instance starts (cold start)
# and reused for subsequent invocations (warm starts).
gmail_service_instance = None
agent_engine_client_instance = None
# firestore_db_client is imported directly from services.firestore_service

try:
    if not all([PROJECT_ID, LOCATION, AGENT_ENGINE_ID, TARGET_USER_EMAIL, SECRET_NAME_GMAIL_CREDS, FIRESTORE_HISTORY_COLLECTION]):
         raise ValueError("FATAL STARTUP: Missing one or more critical environment variables (PROJECT_ID, LOCATION, AGENT_ENGINE_ID, TARGET_USER_EMAIL, SECRET_NAME_GMAIL_CREDS, FIRESTORE_HISTORY_COLLECTION)")
    
    print("Initializing Gmail Service...")
    gmail_service_instance = GmailService().service 
    print("Gmail Service initialized.")

    print(f"Initializing Vertex AI Agent Engine client for Agent ID: {AGENT_ENGINE_ID}...")
    agent_engine_client_instance = create_agent_engine_client() 
    if not agent_engine_client_instance:
        raise ConnectionError("Failed to create agent engine client via services.vertex_ai_service.")
    print("Vertex AI Agent Engine client initialized.")

    if not firestore_db_client: # Check if the imported client is valid
        raise ConnectionError("Firestore client from services.firestore_service is not initialized.")
    print("Firestore client appears to be initialized from services.firestore_service.")


except Exception as e:
    print(f"FATAL STARTUP ERROR: Could not initialize clients: {e}")
    # For Cloud Functions, raising an exception during global scope execution
    # will prevent the function from deploying or starting correctly.
    raise # Propagate the exception to fail the function startup


# --- Main Cloud Function (Now HTTP Triggered) ---
@functions_framework.http
def process_scheduled_email_check(request):
    """
    HTTP-triggered Cloud Function called by Cloud Scheduler to poll for new emails.
    Args:
        request (flask.Request): The HTTP request object. The payload is not typically used
                                 when triggered by Cloud Scheduler with a simple GET/POST.
    Returns:
        A Flask response object (text and status code).
    """
    global gmail_service_instance, agent_engine_client_instance, firestore_db_client

    # function_invocation_id = request.headers.get("Function-Execution-Id", "local-run")
    # print(f"\n-----Scheduled Email Check Triggered (ID: {function_invocation_id})-----\n")
    
    # Ensure global clients were initialized (double check for warm starts where global init might have failed silently)
    if not gmail_service_instance:
        print("CRITICAL RUNTIME ERROR: Gmail service client not initialized. Exiting.")
        return make_response("Internal Server Error: Gmail service not ready.", 500)
    if not agent_engine_client_instance:
        print("CRITICAL RUNTIME ERROR: Agent Engine client not initialized. Exiting.")
        return make_response("Internal Server Error: Agent Engine not ready.", 500)
    if not firestore_db_client:
        print("CRITICAL RUNTIME ERROR: Firestore client not initialized. Exiting.")
        return make_response("Internal Server Error: Firestore client not ready.", 500)

    if not TARGET_USER_EMAIL:
        print("CRITICAL RUNTIME ERROR: TARGET_USER_EMAIL environment variable not set. Cannot proceed.")
        return make_response("Configuration Error: Target user email not set.", 500)
    
    print(f"Polling for new emails for: {TARGET_USER_EMAIL}")

    try:
        # --- 1. Get Last Processed History ID ---
        # Uses Firestore via scripts.history_id_manager.py which uses the global firestore_db_client
        start_history_id = get_last_processed_history_id(TARGET_USER_EMAIL) # Already passes db_client implicitly

        if start_history_id is None:
            print(f"No last_processed_history_id found for {TARGET_USER_EMAIL}. This is the first run or Firestore data was cleared.")
            start_history_id = create_baseline_history_id(gmail_service_instance)
        
        # --- 2. Fetch New Emails Based on Stored History ---
        # get_emails_from_history should use the start_history_id to call users.history.list,
        # filter for UNREAD & INBOX (or target labels), and return full message objects.
        # IMPORTANT: get_emails_from_history MUST now also return the latest historyId from the batch it fetched.
        print(f"Fetching new emails for {TARGET_USER_EMAIL} since stored historyId: {start_history_id}...")
        

        new_emails, latest_history_id_from_batch = get_emails_from_history(
            gmail_service_instance, 
            history_id=start_history_id, # This is used as startHistoryId
        )

        if not new_emails: 
            print(f"No new relevant messages found since historyId {start_history_id} for {TARGET_USER_EMAIL}.")
            # If get_emails_from_history returned a new latest_history_id_from_batch (even if no messages qualified), update Firestore.
            # This historyId comes from the history.list API response.
            if latest_history_id_from_batch and (not start_history_id or int(latest_history_id_from_batch) > int(start_history_id)):
                update_last_processed_history_id(TARGET_USER_EMAIL, latest_history_id_from_batch)
                print(f"Updated Firestore for {TARGET_USER_EMAIL} to {latest_history_id_from_batch} as history advanced but no qualifying messages.")
            return make_response("Polling complete: No new messages of interest.", 200)

        print(f"Found {len(new_emails)} new email(s) to process.")
        
        for email_resource in new_emails: # email_resource is a full message object from get_emails_from_history
            original_message_id = email_resource.get("id")
            email_data = get_email_details(email_resource) # Parses the already fetched full message resource

            # Prevent replying to self
            parsed_sender_email = None
            from_header_value = next((header['value'] for header in email_resource.get("payload", {}).get("headers", []) if header['name'].lower() == 'from'), None)
            if from_header_value:
                match = os.path.splitext(from_header_value)[0] # Basic parsing, might need regex for "Name <email>"
                if '<' in from_header_value and '>' in from_header_value:
                    match = from_header_value[from_header_value.find('<')+1:from_header_value.find('>')]
                else:
                    match = from_header_value # if it's just an email
                parsed_sender_email = match.lower().strip()

            if parsed_sender_email == TARGET_USER_EMAIL.lower():
                print(f"Skipping email {original_message_id} because it was sent by the bot itself ({TARGET_USER_EMAIL}). Marking as read if UNREAD.")
                if 'UNREAD' in email_resource.get('labelIds', []):
                    mark_email_as_read_in_gmail(gmail_service_instance, TARGET_USER_EMAIL, original_message_id)
                continue

            print(f"Processing message ID: {original_message_id}, Subject: {email_data.get('subject')}")
            
            thread_id = email_data.get("thread_id")
            agent_user_id_for_session = thread_id if thread_id else email_data.get("sender_email", f"no_thread_{original_message_id}")

            agent_session_dict = get_agent_session(agent_engine_client_instance, agent_user_id_for_session)
            agent_session_name = agent_session_dict.get("name") # Expecting full session resource name

            agent_response_text = make_agent_call(
                agent_engine_client_instance, 
                agent_user_id_for_session, 
                agent_session_name, 
                email_data # Pass the dict containing 'body' etc.
            )
            
            reply_sent = send_mail(
                gmail_service_instance,
                to_email=email_data.get("from"), # Extracted "From" header value
                from_email=TARGET_USER_EMAIL,    # Reply as the alias
                subject=email_data.get("subject"), # Your send_mail should handle "Re:"
                content=agent_response_text,
                thread_id=thread_id, # For threading
                message_id_header=email_data.get("message_id_header") # For In-Reply-To
            )

            if reply_sent:
                print(f"Reply sent for message {original_message_id}. Marking as read.")
                mark_email_as_read_in_gmail(gmail_service_instance, TARGET_USER_EMAIL, original_message_id)
            else:
                print(f"Failed to send reply for message {original_message_id}. It will remain unread.")
                # Consider if this failure should prevent historyId update or trigger a retry for the whole batch
        
        # --- 4. Update History ID in Firestore ---
        # Update with the latest historyId obtained from processing this batch
        if latest_history_id_from_batch and (not start_history_id or int(latest_history_id_from_batch) > int(start_history_id)):
            print(f"Updating last_processed_history_id for {TARGET_USER_EMAIL} to {latest_history_id_from_batch} in Firestore.")
            update_last_processed_history_id(TARGET_USER_EMAIL, latest_history_id_from_batch)
        else:
            print(f"No newer historyId from batch ({latest_history_id_from_batch}) to update in Firestore. Current start_history_id was {start_history_id}. This is okay if no new history events occurred.")
        
        return make_response(f"Polling complete: {len(new_emails)} email(s) potentially handled.", 200)

    except SystemExit as se:
        print(f"SystemExit during processing: {se}")
        # This was likely from a startup check, allow it to fail the function
        # and be caught by Cloud Run's error reporting.
        # Returning 500 will tell Scheduler the job instance failed.
        return make_response(f"Critical startup error led to exit: {se}", 500)
    except Exception as e:
        print(f"-----Unhandled error during scheduled email check: {e}-----")
        # Return an error status to Cloud Scheduler so it knows the job failed.
        # This might trigger retries based on Scheduler's config.
        return make_response(f"Error during scheduled check: {e}", 500)
