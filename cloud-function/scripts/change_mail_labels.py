from csv import Error

def mark_as_read(service,notified_email_address, mail_id):
  try:
    (
      service.users()
        .messages()
        .modify(userId=notified_email_address,id=mail_id, body={'removeLabelIds': ['UNREAD']}).execute()
    )
  except Error as e:
    print(f"An error occurred in mark as read: {e}")

