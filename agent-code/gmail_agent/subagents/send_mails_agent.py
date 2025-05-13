from google.adk.agents import Agent
from pydantic import BaseModel, Field
from scripts.send_mail import send_email


class EmailOutput(BaseModel):
    subject: str = Field(description="The subject of the email.")
    body: str = Field(description="The capital of the country.")

gmail_agent = Agent(
    name='gmail_agent',
    model='gemini-2.0-flash-001',
    description='',
    tools=[],
    instruction=
    """
    
    """,
)
