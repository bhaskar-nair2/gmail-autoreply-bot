from services.firestore_service import firestore_db_client

def get_session_id(thread_id):
    """
    Retrieves the session for a given thread from Firestore or creates a new one
    """
    session_id = ""
    new = False
    try:
        # Assuming we have a way to get the message ID or thread ID
        # For example, from the incoming request or context

        # Fetch the session from Firestore or any other storage
        session_ref = firestore_db_client.collection("sessions").document(thread_id)
        session_data = session_ref.get()

        if session_data.exists:
            print(f"Session found for thread {thread_id}: {session_data.to_dict()}")
            session_id = session_data.to_dict().get("session_id")
        else:
            print(f"Creating new session for {thread_id}.")
            new = True
        
        return session_id, new

    except Exception as e:
        print(f"Error retrieving session for message {thread_id}: {e}")
        return None

def save_new_session(session_id, thread_id):
    session_ref = firestore_db_client.collection("sessions").document(thread_id)
    session_ref.set({"thread_id": thread_id, "session_id": session_id})
    

def get_agent_session(agent_enging, thread_id):
    print("Getting Session")
    session_id, new = get_session_id(thread_id)
    if new:
        session = agent_enging.create_session(user_id=thread_id)
        save_new_session(session.get("id"), thread_id)
    else:
        session = agent_enging.get_session(user_id=thread_id, session_id=session_id)
    return session

