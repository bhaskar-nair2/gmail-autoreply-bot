import os
import asyncio
from dotenv import load_dotenv

from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService

from utils import call_agent_async
from gmail_auth.gmail_auth import refresh_gmail_token

load_dotenv()
# refresh_gmail_token()

from gmail_agent import gmail_agent

USER_ID = os.environ.get("TARGET_USER_EMAIL")

db_url = "sqlite:///./memory_agent.db"
session_service = DatabaseSessionService(db_url=db_url)

init_state = {}

async def main_async():
  APP_NAME = "Gmail Agent"
  
  # Get all the existing sessions for this app with this user
  existing_sessions = session_service.list_sessions(
    app_name= APP_NAME,
    user_id= USER_ID,
  )

  if existing_sessions and len(existing_sessions.sessions) > 0:
    SESSION_ID = existing_sessions.sessions[0].id
    print(f"=== Using existing session with ID: {SESSION_ID}")
  else:
    new_session = session_service.create_session(
      app_name= APP_NAME,
      user_id= USER_ID,
      state= init_state
    )
    SESSION_ID = new_session.id
    print(f"Created new Session with ID: {SESSION_ID}")
    
  runner = Runner(
    app_name= APP_NAME,
    agent= gmail_agent,
    session_service=session_service
  )
  
  print("\n ++++ Welcome to Memory Agent Chat ++++")
  print("Add a reminder to save to agent")
  print("Type exit to exit the chat")
  
  while True:
    user_input = input("You: ")
    if user_input.lower() == "exit":
      print("\n Your session is saved")
      break
    await call_agent_async(runner, USER_ID, SESSION_ID, user_input)
  
  
if __name__ == "__main__":
  asyncio.run(main_async())
