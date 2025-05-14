import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# Use the application default credentials.
cred = credentials.ApplicationDefault()

firebase_admin.initialize_app(cred)

global firestore_db_client 
firestore_db_client = firestore.client(database_id="gmail-bot-database")

# Test
def main():
    # Example usage
    doc_ref = firestore_db_client.collection("sessions").document("123")
    doc_ref.set({"thread_id": "123", "session_id": "test_session"})

if __name__ == "__main__":
    main()
