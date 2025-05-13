from google.genai import types
from google.adk.runners import Runner, Event


async def call_agent_async(runner : Runner, user_id, session_id, query):
  new_message = types.Content(role="user", parts=[types.Part(text=query)])
  
  try:
    async for event in runner.run_async(
    user_id=user_id,
    session_id=session_id,
    new_message=new_message
    ):
      await process_bot_response(event)
  except Exception as e:
    print(f"Some error occoured: {e}")


async def process_bot_response(event: Event):
   print(f"Event ID: {event.id}, Author: {event.author}")
   if event.content:
     if event.content.parts[0].text:
          print(f"Text:\n{event.content.parts[0].text}")
     elif event.content.parts:
          print(f"Parts:\n{event.content.parts}")
   if event.is_final_response():
          print("\n==============================\n")
   
   