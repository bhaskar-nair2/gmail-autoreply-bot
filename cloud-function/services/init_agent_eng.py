import os
import re
import vertexai
from vertexai import agent_engines


def create_agent_engine_client():
  """
  Create an Agent Engine client using the provided credentials.
  """
  PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT") 
  LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1") 
  AGENT_ENGINE_ID = os.environ.get("AGENT_ENGINE_ID")
  
  agent_engine_client = None
  
  try:
      if PROJECT_ID and LOCATION and AGENT_ENGINE_ID:
          pass
          print(f"Initializing Vertex AI for project {PROJECT_ID} in {LOCATION}...")
          vertexai.init(project=PROJECT_ID, location=LOCATION)
          agent_engine_client = agent_engines.get(AGENT_ENGINE_ID)
          print(agent_engine_client)
          print(f"Initialized Vertex AI and Agent Engine client for: {AGENT_ENGINE_ID}")
          return agent_engine_client
      else:
          print("ERROR: Missing one or more environment variables for Vertex AI init: GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION, AGENT_ENGINE_ID")
          agent_engine_client = None
  except Exception as e:
      print(f"FATAL: Could not initialize Vertex AI or Agent Engine: {e}")
      agent_engine_client = None
