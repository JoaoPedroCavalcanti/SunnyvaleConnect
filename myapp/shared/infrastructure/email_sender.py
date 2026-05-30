"""Email sender abstraction so services don't talk to Django mail directly."""

from abc import ABC, abstractmethod
from datetime import datetime

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone


class IEmailSender(ABC):
    @abstractmethod
    def send_visitor_invite(
        self,
        to_email: str,
        link: str,
        user_name: str,
        datetime_checkin: datetime,
        visitor_name: str,
    ) -> None: ...

    @abstractmethod
    def send_checkin_notification(
        self, to_email: str, user_name: str, visitor_name: str
    ) -> None: ...

    @abstractmethod
    def send_checkout_notification(
        self, to_email: str, user_name: str, visitor_name: str
    ) -> None: ...

    @abstractmethod
    def send_delivery_notification(
        self,
        to_email: str,
        user_name: str,
        delivery_platform: str | None,
        delivery_from: str | None,
    ) -> None: ...


class DjangoEmailSender(IEmailSender):
    def _send(self, subject: str, message: str, to_email: str) -> None:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [to_email])

    def send_visitor_invite(
        self,
        to_email: str,
        link: str,
        user_name: str,
        datetime_checkin: datetime,
        visitor_name: str,
    ) -> None:
        subject = "Welcome to Sunnyvale"
        message = (
            f"Dear {visitor_name},\n\n"
            f"You have been invited by {user_name} to visit Sunnyvale. "
            f"Please use the following link to check-in at the scheduled time: {link}.\n"
            f"Note: The link will only be accessible after your scheduled check-in time: {datetime_checkin}.\n\n"
            f"Thank you and we look forward to your visit!\n"
            f"Best regards,\n"
            f"Sunnyvale Management"
        )
        self._send(subject, message, to_email)

    def send_checkin_notification(
        self, to_email: str, user_name: str, visitor_name: str
    ) -> None:
        subject = "Check-in notification"
        message = (
            f"Dear {user_name},\n\n"
            f"{visitor_name} checked-in in Sunny Vale at time: {timezone.now()}\n"
            f"Best regards,\n"
            f"Sunnyvale Management"
        )
        self._send(subject, message, to_email)

    def send_checkout_notification(
        self, to_email: str, user_name: str, visitor_name: str
    ) -> None:
        subject = "Check-out notification"
        message = (
            f"Dear {user_name},\n\n"
            f"{visitor_name} checked-out from Sunny Vale at time: {timezone.now()}\n"
            f"Best regards,\n"
            f"Sunnyvale Management"
        )
        self._send(subject, message, to_email)

    def send_delivery_notification(
        self,
        to_email: str,
        user_name: str,
        delivery_platform: str | None,
        delivery_from: str | None,
    ) -> None:
        subject = "Delivery notification"
        message = (
            f"Dear {user_name},\n\n"
            f"We would like to inform you that a delivery has arrived for you at the entrance of Sunnyvale.\n"
            "Delivery Details:\n"
        )
        if delivery_platform:
            message += f" • Delivery Service: {delivery_platform}\n"
        if delivery_from:
            message += f" • Delivery From: {delivery_from}\n"
        received_at = timezone.now().strftime("%B %d, %Y at %I:%M %p")
        message += f" • Received At: {received_at}\n"
        message += "Best regards,\nSunnyvale Management"
        self._send(subject, message, to_email)
