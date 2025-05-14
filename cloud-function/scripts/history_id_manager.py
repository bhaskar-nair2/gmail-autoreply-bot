# scripts/history_id_manager.py
from google.cloud import firestore
import time

# Note: The firestore_db client should be initialized in your main Cloud Function file
# and passed to these functions. The collection_name should also be passed or configured.

def get_last_processed_history_id(db_client: firestore.Client, user_email: str, collection_name: str):
    """
    Retrieves the last processed historyId for a given user from Firestore.

    Args:
        db_client: An initialized Firestore client.
        user_email: The email address of the user whose historyId is being fetched.
                    This will be used as the document ID in Firestore.
        collection_name: The name of the Firestore collection storing historyIds.

    Returns:
        The last processed historyId as a string, or None if not found.
    """
    if not db_client:
        print("ERROR (history_id_manager): Firestore client is not provided.")
        return None
    if not user_email:
        print("ERROR (history_id_manager): user_email cannot be empty.")
        return None
    if not collection_name:
        print("ERROR (history_id_manager): collection_name cannot be empty.")
        return None

    try:
        doc_ref = db_client.collection(collection_name).document(user_email)
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
            print(f"No historyId document found for user '{user_email}' in Firestore collection '{collection_name}'. Will need to establish a baseline.")
            return None
    except Exception as e:
        print(f"Error getting historyId for '{user_email}' from Firestore: {e}")
        # Depending on the error, you might want to raise it or handle differently
        return None

def update_last_processed_history_id(db_client: firestore.Client, user_email: str, new_history_id: str, collection_name: str):
    """
    Updates/creates the last processed historyId for a given user in Firestore.

    Args:
        db_client: An initialized Firestore client.
        user_email: The email address of the user whose historyId is being updated.
                    This will be used as the document ID.
        new_history_id: The new historyId to store.
        collection_name: The name of the Firestore collection.
    """
    if not db_client:
        print("ERROR (history_id_manager): Firestore client is not provided for update.")
        return False
    if not user_email:
        print("ERROR (history_id_manager): user_email cannot be empty for update.")
        return False
    if not new_history_id:
        print("ERROR (history_id_manager): new_history_id cannot be empty for update.")
        return False
    if not collection_name:
        print("ERROR (history_id_manager): collection_name cannot be empty for update.")
        return False

    try:
        doc_ref = db_client.collection(collection_name).document(user_email)
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
