# scripts/history_id_manager.py
import os
import time

from google.cloud import firestore
from services.firestore_service import firestore_db_client as db_client

# Note: The firestore_db client should be initialized in your main Cloud Function file
# and passed to these functions. The collection_name should also be passed or configured.

HISTORY_ID_DB = "history_id_storage"

def get_last_processed_history_id(user_email: str):
    """
    Retrieves the last processed historyId for a given user from Firestore.

    Args:
        db_client: An initialized Firestore client.
        user_email: The email address of the user whose historyId is being fetched.
                    This will be used as the document ID in Firestore.

    Returns:
        The last processed historyId as a string, or None if not found.
    """
    try:
        doc_ref = db_client.collection(HISTORY_ID_DB).document(user_email)
        doc = doc_ref.get()

        if doc.exists:
            history_id_data = doc.to_dict()
            last_id = history_id_data.get("lastHistoryId")
            if last_id:
                print(f"Retrieved lastHistoryId '{last_id}' for user '{user_email}' from Firestore.")
                return str(last_id) # Ensure it's a string
            else:
                print(f"Document for '{user_email}' exists but 'lastHistoryId' field is missing or empty.")
                return None
        else:
            print(f"No historyId document found for user '{user_email}' in Firestore collection '{HISTORY_ID_DB}'. Will need to establish a baseline.")
            return None
    except Exception as e:
        print(f"Error getting historyId for '{user_email}' from Firestore: {e}")
        # Depending on the error, you might want to raise it or handle differently
        return None

def update_last_processed_history_id(user_email: str, new_history_id: str):
    """
    Updates/creates the last processed historyId for a given user in Firestore.

    Args:
        db_client: An initialized Firestore client.
        user_email: The email address of the user whose historyId is being updated.
                    This will be used as the document ID.
        new_history_id: The new historyId to store.
        collection_name: The name of the Firestore collection.
    """
    try:
        doc_ref = db_client.collection(HISTORY_ID_DB).document(user_email)
        doc_ref.set({
            "lastHistoryId": str(new_history_id), # Ensure it's stored as a string
            "updatedTimestamp": firestore.SERVER_TIMESTAMP, # Automatically set server-side timestamp
            "updatedEpoch": int(time.time()) # Store client-side epoch for easier querying if needed
        }, merge=True) # merge=True will create if not exists, or update existing fields
        print(f"Successfully updated lastHistoryId to '{new_history_id}' for user '{user_email}' in Firestore.")
        return True
    except Exception as e:
        print(f"Error updating historyId for '{user_email}' in Firestore: {e}")
        return False

def create_baseline_history_id(service):
    try:
        TARGET_USER_EMAIL = os.environ.get("TARGET_USER_EMAIL")
        profile = service.users().getProfile(userId=TARGET_USER_EMAIL).execute()
        current_mailbox_hid = profile.get('historyId')
        if not current_mailbox_hid:
            raise ValueError("Could not retrieve current historyId from Gmail profile.")
        print(f"Setting baseline historyId for {TARGET_USER_EMAIL} to current mailbox state: {current_mailbox_hid}")
        update_last_processed_history_id(TARGET_USER_EMAIL, current_mailbox_hid)
        return current_mailbox_hid
    except Exception as e_profile:
        print(f"CRITICAL: Error getting profile historyId for baseline for {TARGET_USER_EMAIL}: {e_profile}.")
