import os
import json
from dotenv import load_dotenv

    
def get_final_response(event):
    """Pretty prints an event with truncation for long content."""
    if "content" not in event:
        print(f"[{event.get('author', 'unknown')}]: {event}")
        return
        
    author = event.get("author", "unknown")
    parts = event["content"].get("parts", [])
    final_response = ''
    
    for part in parts:
        if "text" in part:
            text = part["text"]
            final_response += text
        # ! Other types are ignored for now
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
    return final_response

def make_agent_call(service, thread_id, session_id, message):
    """Calls the AI agent with the provided message and session."""
    print("!!!! Calling Reasoning Agent !!!!")
    try:
        extracted_text = ""
        
        for event in service.stream_query(
            user_id=thread_id,
            session_id=session_id,
            message=f"{message}",
        ):
            extracted_text= get_final_response(event)
        
        return extracted_text
    except Exception as e:
        print(f"Error calling AI agent: {e}")
        return None



if __name__ == "__main__":
    # This is a placeholder for the actual function call.
    # In a real scenario, this would be triggered by an event (e.g., a new email).
   
    response = make_agent_call("Tell me various things about Labradors", user_id="test_session2")
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
