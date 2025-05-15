import base64
from email.message import EmailMessage

from googleapiclient.errors import HttpError

def send_mail(service, *, to_email, from_email, subject, content):
  """Create and send an email message
  Print the returned  message id
  Returns: Message object, including message id

  Load pre-authorized user credentials from the environment.
  TODO(developer) - See https://developers.google.com/identity
  for guides on implementing OAuth2 for the application.
  """

  try:
    # encoded message
    message = EmailMessage()
    message.set_content(content)
    message["To"] = to_email
    message["From"] = from_email
    message["Subject"] = subject
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    create_message = {"raw": encoded_message}
    
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
  
  send_mail(to_email, from_email, subject, content)
