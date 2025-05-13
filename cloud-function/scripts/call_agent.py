import os
import json
from dotenv import load_dotenv

import vertexai
from vertexai import agent_engines 

load_dotenv()

# --- Configuration (Set as Environment Variables in Cloud Function) ---
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT") # Automatically set by Cloud Functions
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1") # Default if not set
AGENT_ENGINE_ID = os.environ.get("AGENT_ENGINE_ID") # Full resource name of your Reasoning Engine


try:
    if PROJECT_ID and LOCATION and AGENT_ENGINE_ID:
        print(f"Initializing Vertex AI for project {PROJECT_ID} in {LOCATION}...")
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        adk_app = agent_engines.get(AGENT_ENGINE_ID)
        print(f"Initialized Vertex AI and Agent Engine client for: {adk_app.resource_name}")
    else:
        print("ERROR: Missing one or more environment variables for Vertex AI init: GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION, AGENT_ENGINE_ID")
        adk_app = None
except Exception as e:
    print(f"FATAL: Could not initialize Vertex AI or Agent Engine: {e}")
    adk_app = None
    
def pretty_print_event(event):
    """Pretty prints an event with truncation for long content."""
    if "content" not in event:
        print(f"[{event.get('author', 'unknown')}]: {event}")
        return
        
    author = event.get("author", "unknown")
    parts = event["content"].get("parts", [])
    
    for part in parts:
        if "text" in part:
            text = part["text"]
            # Truncate long text to 200 characters
            if len(text) > 200:
                text = text[:197] + "..."
            print(f"[{author}]: {text}")
        elif "functionCall" in part:
            func_call = part["functionCall"]
            print(f"[{author}]: Function call: {func_call.get('name', 'unknown')}")
            # Truncate args if too long
            args = json.dumps(func_call.get("args", {}))
            if len(args) > 100:
                args = args[:97] + "..."
            print(f"  Args: {args}")
        elif "functionResponse" in part:
            func_response = part["functionResponse"]
            print(f"[{author}]: Function response: {func_response.get('name', 'unknown')}")
            # Truncate response if too long
            response = json.dumps(func_response.get("response", {}))
            if len(response) > 100:
                response = response[:97] + "..."
            print(f"  Response: {response}")

def call_ai_agent(user_query, user_id='test_session'):
  """Call the AI agent to process an email and return the response."""
  if adk_app is None:
      print("ERROR: Agent Engine client is not initialized. Exiting.")
      return "Agent Engine client is not initialized."
  
  session_id = None
  session = None
  # 
  sessions = adk_app.list_sessions(user_id=user_id).get("sessions", [])
  print(sessions)
  
#   if len(sessions) > 0 :
#     session_id = sessions[0].get("id")
#   else:
#     session = adk_app.create_session(user_id=user_id)
#     session_id = session.get("id")
#     print(f"Created new session with ID: {session_id}")
    
  full_response_text = ""
  session = adk_app.create_session(user_id=user_id)
  print(session)
  
  for event in adk_app.stream_query(input={"messages": [("user", user_query)]}):
    print(event)
        
  return full_response_text.strip()


if __name__ == "__main__":
    # This is a placeholder for the actual function call.
    # In a real scenario, this would be triggered by an event (e.g., a new email).
   
    response = call_ai_agent("Tell me various things about Labradors", user_id="test_session2")
    print(f"Response from AI agent: {response}")
    
    # print(adk_app.operation_schemas())
    
    # print(adk_app.list())
    # adk_app.delete()
    
    """
    <vertexai.agent_engines._agent_engines.AgentEngine object at 0x0000023EE4A791C0> 
    resource name: projects/661065862360/locations/us-central1/reasoningEngines/7620310471836434432, 

    <vertexai.agent_engines._agent_en4432, <vertexai.agent_engines._agent_engines.AgentEngine object at 0x0000023EE4A793D0>
    resource name: projects/661065862360/locations/us-central1/reasoningEngines/8933109763214934016, 

    <vertexai.agent_engines._agent_engines.AgentEngine object at 0x0000023EE4A78FE0>
    resource name: projects/661065862360/locations/us-central1/reasoningEngines/3589448067851485184, 

    <vertexai.agent_engines._agent_engines.AgentEngine object at 0x0000023EE4A79460>
    resource name: projects/661065862360/locations/us-central1/reasoningEngines/6242068248372707328
    """
