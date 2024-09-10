from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

def send_delivery_notification(to_email, user_name, delivery_platform=None, delivery_from=None):
    subject = 'Delivery notification'
    
    # Construir a mensagem
    message = (
        f"Dear {user_name},\n\n"
        f"We would like to inform you that a delivery has arrived for you at the entrance of Sunnyvale.\n"
        "Delivery Details:\n"
    )
    
    if delivery_platform:
        message += f" • Delivery Service: {delivery_platform}\n"
    
    if delivery_from:
        message += f" • Delivery From: {delivery_from}\n"
    
    received_at = timezone.now().strftime('%B %d, %Y at %I:%M %p')
    message += f" • Received At: {received_at}\n"
    message += "Best regards,\nSunnyvale Management"

    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [to_email]
    
    # Enviar email
    send_mail(subject, message, from_email, recipient_list)