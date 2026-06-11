"""Email sender abstraction so services don't talk to Django mail directly."""

import logging
from abc import ABC, abstractmethod
from datetime import datetime

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

logger = logging.getLogger(__name__)


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

    @abstractmethod
    def send_household_join_request(
        self,
        to_email: str,
        holder_name: str,
        requester_name: str,
        apartment: str,
        block: str,
    ) -> None: ...

    @abstractmethod
    def send_household_creation_request(
        self,
        to_email: str,
        requester_name: str,
        apartment: str,
        block: str,
    ) -> None: ...

    @abstractmethod
    def send_household_request_approved(
        self,
        to_email: str,
        requester_name: str,
        apartment: str,
        block: str,
    ) -> None: ...

    @abstractmethod
    def send_household_request_rejected(
        self,
        to_email: str,
        requester_name: str,
        apartment: str,
        block: str,
        reason: str,
    ) -> None: ...


class DjangoEmailSender(IEmailSender):
    """SMTP-backed sender. Failures are logged and swallowed so a flaky mail
    server never breaks the request that triggered the side-effect."""

    def _send(self, subject: str, message: str, to_email: str) -> None:
        if not to_email:
            logger.warning("Skipping email '%s': empty recipient.", subject)
            return
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [to_email],
                fail_silently=False,
            )
        except Exception:
            logger.exception(
                "Failed to send email '%s' to %s", subject, to_email
            )

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

    def _format_unit(self, apartment: str, block: str) -> str:
        return f"Apt {apartment} / Block {block}" if block else f"Apt {apartment}"

    def send_household_join_request(
        self, to_email, holder_name, requester_name, apartment, block
    ) -> None:
        unit = self._format_unit(apartment, block)
        subject = "New resident request"
        message = (
            f"Dear {holder_name},\n\n"
            f"{requester_name} requested to join your household ({unit}).\n"
            f"Open the app to approve or reject the request.\n\n"
            f"Best regards,\nSunnyvale Management"
        )
        self._send(subject, message, to_email)

    def send_household_creation_request(
        self, to_email, requester_name, apartment, block
    ) -> None:
        unit = self._format_unit(apartment, block)
        subject = "New household creation request"
        message = (
            f"Hello,\n\n"
            f"{requester_name} requested to register a new household ({unit}).\n"
            f"Open the admin panel to approve or reject the request.\n\n"
            f"Best regards,\nSunnyvale Management"
        )
        self._send(subject, message, to_email)

    def send_household_request_approved(
        self, to_email, requester_name, apartment, block
    ) -> None:
        unit = self._format_unit(apartment, block)
        subject = "Your account is approved"
        message = (
            f"Dear {requester_name},\n\n"
            f"Your request to join {unit} was approved. "
            f"You can now log in and use Sunnyvale.\n\n"
            f"Best regards,\nSunnyvale Management"
        )
        self._send(subject, message, to_email)

    def send_household_request_rejected(
        self, to_email, requester_name, apartment, block, reason
    ) -> None:
        unit = self._format_unit(apartment, block)
        subject = "Your request was rejected"
        message = (
            f"Dear {requester_name},\n\n"
            f"Your request to join {unit} was rejected.\n"
        )
        if reason:
            message += f"Reason: {reason}\n"
        message += "\nBest regards,\nSunnyvale Management"
        self._send(subject, message, to_email)
