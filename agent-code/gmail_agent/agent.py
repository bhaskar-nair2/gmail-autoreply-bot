from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

from .subagents.send_mails_agent import send_mail_agent


gmail_agent = Agent(
    name='gmail_agent',
    model='gemini-2.0-flash-001',
    description='',
    tools=[
        AgentTool(send_mail_agent)
        ],
    instruction=
    """
    """,
)

#  Send mail to b.bhaskar.nair@gmail.com about pending payment
