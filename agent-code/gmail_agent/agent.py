from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

from .subagents.send_mails_agent import send_mail_agent


gmail_agent = Agent(
    name='gmail_agent',
    model='gemini-2.0-flash-001',
    description='You respond to emails for me. ',
    tools=[
        # AgentTool(send_mail_agent)
        ],
    instruction=
    """
    You are a Gmail agent. You respond to emails for me.
    You recieve a payload containing the email subject, body and sender.
    You will respond to the email with a reply.
    """,
)

#  Send mail to b.bhaskar.nair@gmail.com about pending payment
