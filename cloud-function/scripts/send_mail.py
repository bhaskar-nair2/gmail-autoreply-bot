import base64
from email.message import EmailMessage

from googleapiclient.errors import HttpError
from .gmail_service import instance


def send_email(message:EmailMessage):
  """Create and send an email message
  Print the returned  message id
  Returns: Message object, including message id

  Load pre-authorized user credentials from the environment.
  TODO(developer) - See https://developers.google.com/identity
  for guides on implementing OAuth2 for the application.
  """

  try:
    service = instance.service
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
  message["From"] = from_email
  message["Subject"] = subject
  
  send_email( message)
