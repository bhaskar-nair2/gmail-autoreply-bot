# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
from dotenv import load_dotenv
import vertexai
from vertexai import agent_engines
from vertexai.preview import reasoning_engines
import logging
from dotenv import set_key
from gmail_agent.agent import gmail_agent

load_dotenv()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION")
STAGING_BUCKET = os.getenv("STAGING_BUCKET")
# Define the path to the .env file relative to this script
ENV_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))

vertexai.init(
    project=GOOGLE_CLOUD_PROJECT,
    location=GOOGLE_CLOUD_LOCATION,
    staging_bucket=STAGING_BUCKET,
)

# Function to update the .env file
def update_env_file(agent_engine_id, env_file_path):
    """Updates the .env file with the agent engine ID."""
    try:
        set_key(env_file_path, "AGENT_ENGINE_ID", agent_engine_id)
        print(f"Updated AGENT_ENGINE_ID in {env_file_path} to {agent_engine_id}")
    except Exception as e:
        print(f"Error updating .env file: {e}")

print("deploying app...")

app = reasoning_engines.AdkApp(
    agent= gmail_agent,
    enable_tracing=True,
)

logging.debug("deploying agent to agent engine:")

remote_app = agent_engines.create(
    app,
    display_name="gmail_agent",
    requirements=[
        "google-cloud-aiplatform[adk,agent-engines,llama-index]==1.90.0",
        "google-adk",
        "python-dotenv",
        "google-auth",
        "tqdm",
        "requests",
        "pydantic-settings",
        "tabulate",
        "requests",
        "cloudpickle==3.0"
    ],
    extra_packages=[
        "./gmail_agent",
    ],
)

# log remote_app
logging.info(f"Deployed agent to Vertex AI Agent Engine successfully, resource name: {remote_app.resource_name}")

# Update the .env file with the new Agent Engine ID
update_env_file(remote_app.resource_name, ENV_FILE_PATH)
