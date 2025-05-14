from google.adk.agents import Agent
from pydantic import BaseModel, Field
from scripts.send_mail import send_email


send_mail_agent = Agent(
    name='send_mail_agent',
    model='gemini-2.0-flash-001',
    description='',
    tools=[send_email],
    instruction=
    """
    Based on the input from previous node, generate email_content, subject and get the recipient email then send the email using the send_email tool.
    
    Make sure you extract the recipient email from the user input
    
    If you are not sure about the recipient email, ask the user to confirm the email address.
    If the user does not provide a recipient email, ask them to provide one.
    
    You have access to the following tools:
    1. send_email: For sending emails
    """,
)
