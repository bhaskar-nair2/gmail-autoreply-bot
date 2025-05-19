import base64
from email.message import EmailMessage
import string

from googleapiclient.errors import HttpError

def send_mail(service, *, to_email, from_email, subject, content, thread_id=None, message_id_header = None):
  """Create and send an email message
  Print the returned  message id
  Returns: Message object, including message id

  Load pre-authorized user credentials from the environment.
  TODO(developer) - See https://developers.google.com/identity
  for guides on implementing OAuth2 for the application.
  """
  print("Sending Email")
  try:
    # encoded message
    message = EmailMessage()
    message.set_content(f"{content}")
    message["To"] = to_email
    message["Subject"] = process_subject(subject)
    
    # Set headers for correct threading
    if message_id_header:
      message["In-Reply-To"] = message_id_header
      message["References"] = message_id_header

        
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    create_message = {"raw": encoded_message}
    
    # Ensure the reply stays in the same thread
    if thread_id:
        create_message["threadId"] = thread_id
    
    send_message = (
        service.users()
        .messages()
        .send(userId="me", body=create_message)
        .execute()
    )
    print(f'Message sent with Id: {send_message["id"]}')
  except HttpError as error:
    print(f"n error occurred in send mails: {error}")
    send_message = None
  else:
    return True

def process_subject(subject = "") -> string:
  if subject and not subject.lower().startswith("re:"):
    return f"Re: {subject}"
  else:
    return subject

# For testing purposes
if __name__ == "__main__":
  to_email = "b.bhaskar.nair@gmail.com"
  from_email = "bhaskarnair.work@gmail.com" 
  subject, content = "TEST", "This is a test email"
  
  send_mail(to_email, from_email, subject, content)
