from csv import Error

def mark_as_read(service, notified_email_address, mail_id):
  try:
    (
      # ? Remove unread and bot response label 
      service.users()
        .messages()
        .modify(userId=notified_email_address,
                id=mail_id, 
                body={'removeLabelIds': ['UNREAD','Label_6682199651960682642']}
        ).execute()
    )
  except Error as e:
    print(f"An e  rror occurred in mark as read: {e}")
