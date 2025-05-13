from google.adk.agents import Agent
from .scripts.gmail_service import initialize_service
from .scripts.send_mail import send_email

initialize_service()

gmail_agent = Agent(
    name='gmail_agent',
    model='gemini-2.0-flash-001',
    description='You are an agent that can send emails using your tools',
    tools=[send_email],
    instruction=
    """
    Based on the user input, generate email_content, subject and get the recipient email then send the email using the send_email tool.
    Make sure you extract the recipient email from the user input
    
    If you are not sure about the recipient email, ask the user to confirm the email address.
    If the user does not provide a recipient email, ask them to provide one.
    
    You have access to the following tools:
    1. send_email: For sending emails
    """,
)

#  Send mail to b.bhaskar.nair@gmail.com about pending payment
