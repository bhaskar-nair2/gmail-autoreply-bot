import base64
from email.message import EmailMessage

from googleapiclient.errors import HttpError
from google.adk.tools import ToolContext
from .gmail_service import instance 


def send_email(recipient_email : str,subject : str,email_content : str, tool_context: ToolContext):
  """
  A simple tool to send an email
  
  Args:
    - recipient_email (str): Email address of the recipient
    - subject (str): Subject of the email
    - email_content (str): Main contents of the email
  """
  
  service = instance.service
  
  message = EmailMessage()
  message.set_content(email_content)
  message["To"] = recipient_email
  message["Subject"] = subject
  # message["From"] = tool_context.state["user_id"]

  try:
    # encoded message
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    create_message = {"raw": encoded_message}
    # pylint: disable=E1101
    send_message = (
        service.users()
        .messages()
        .send(userId="me", body=create_message)
        .execute()
    )
    print(f'Message sent with Id: {send_message["id"]}')
  except HttpError as error:
    print(f"An error occurred: {error}")
    send_message = None
  return send_message

# For testing purposes
if __name__ == "__main__":
  to_email = "b.bhaskar.nair@gmail.com"
  from_email = "bhaskarnair.work@gmail.com" 
  subject, content = "TEST", "This is a test email"
  
  message = EmailMessage()
  message.set_content(content)
  message["To"] = to_email
  message["Subject"] = subject
  
  send_email(message)
