from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone


def send_link_email(to_email, link_email, user_name, datetime_checkin, visitor_name):
    subject = 'Welcome to Sunnyvale'
    message = (f"Dear {visitor_name},\n\n"
               f"You have been invited by {user_name} to visit Sunnyvale. "
               f"Please use the following link to check-in at the scheduled time: {link_email}.\n"
               f"Note: The link will only be accessible after your scheduled check-in time: {datetime_checkin}.\n\n"
               f"Thank you and we look forward to your visit!\n"
               f"Best regards,\n"
               f"Sunnyvale Management")
    
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [to_email]
    
    send_mail(subject, message, from_email, recipient_list)
    
def send_checkin_notification(to_email, user_name, visitor_name):
    subject = 'Check-in notification'
    message = (f"Dear {user_name},\n\n"
               f"{visitor_name} checked-in in Sunny Vale at time: {timezone.now()}\n"
               f"Best regards,\n"
               f"Sunnyvale Management")
    
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [to_email]
    
    send_mail(subject, message, from_email, recipient_list)
    
def send_checkout_notification(to_email, user_name, visitor_name):
    subject = 'Check-out notification'
    message = (f"Dear {user_name},\n\n"
               f"{visitor_name} checked-out from Sunny Vale at time: {timezone.now()}\n"
               f"Best regards,\n"
               f"Sunnyvale Management")
    
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [to_email]
    
    send_mail(subject, message, from_email, recipient_list)