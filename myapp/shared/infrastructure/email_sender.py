"""Email sender abstraction so services don't talk to Django mail directly."""

import logging
from abc import ABC, abstractmethod
from datetime import date, datetime, time
from email.mime.image import MIMEImage

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail
from django.utils import timezone

from shared.infrastructure.email_renderer import render_email

logger = logging.getLogger(__name__)

_VISITOR_QR_CONTENT_ID = "visitor_qr"


class IEmailSender(ABC):
    @abstractmethod
    def send_visitor_qr_access(
        self,
        to_email: str,
        access_code: str,
        qr_png: bytes,
        user_name: str,
        datetime_checkin: datetime,
        datetime_checkout: datetime,
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
        *,
        apartment: str = "",
        block: str = "",
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

    @abstractmethod
    def send_reservation_approved(
        self,
        to_email: str,
        user_name: str,
        resource_name: str,
        reservation_date: date,
        start_time: time | None,
        end_time: time | None,
    ) -> None: ...

    @abstractmethod
    def send_reservation_rejected(
        self,
        to_email: str,
        user_name: str,
        resource_name: str,
        reservation_date: date,
        start_time: time | None,
        end_time: time | None,
        reason: str = "",
    ) -> None: ...

    @abstractmethod
    def send_service_request_responded(
        self,
        to_email: str,
        requester_name: str,
        title: str,
        action: str,
        response: str,
        responder_name: str,
    ) -> None: ...

    @abstractmethod
    def send_visitor_arrival_notification(
        self,
        to_email: str,
        user_name: str,
        visitor_name: str,
    ) -> None: ...

    @abstractmethod
    def send_visitor_qr_sent_notification(
        self,
        to_email: str,
        user_name: str,
        visitor_name: str,
        visitor_email: str,
    ) -> None: ...

    @abstractmethod
    def send_email_verification_code(
        self,
        to_email: str,
        user_name: str,
        code: str,
    ) -> None: ...


class DjangoEmailSender(IEmailSender):
    """SMTP-backed sender. Failures are logged and swallowed so a flaky mail
    server never breaks the request that triggered the side-effect."""

    def _send(
        self,
        subject: str,
        plain_message: str,
        to_email: str,
        *,
        html_message: str,
    ) -> None:
        if not to_email:
            logger.warning("Skipping email '%s': empty recipient.", subject)
            return
        try:
            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [to_email],
                html_message=html_message,
                fail_silently=False,
            )
        except Exception:
            logger.exception(
                "Failed to send email '%s' to %s", subject, to_email
            )

    def _render_and_send(
        self, subject: str, template_name: str, context: dict, to_email: str
    ) -> None:
        html_message, plain_message = render_email(template_name, context)
        self._send(subject, plain_message, to_email, html_message=html_message)

    def send_visitor_qr_access(
        self,
        to_email: str,
        access_code: str,
        qr_png: bytes,
        user_name: str,
        datetime_checkin: datetime,
        datetime_checkout: datetime,
        visitor_name: str,
    ) -> None:
        subject = "Welcome to Sunnyvale"
        checkin_label = timezone.localtime(datetime_checkin).strftime(
            "%B %d, %Y at %I:%M %p"
        )
        checkout_label = timezone.localtime(datetime_checkout).strftime(
            "%B %d, %Y at %I:%M %p"
        )
        access_note = (
            f"Show the QR code or tell the access code to the doorman "
            f"between {checkin_label} and {checkout_label}."
        )
        html_message, _ = render_email(
            "visitor_invite",
            {
                "heading": "You're invited to Sunnyvale",
                "visitor_name": visitor_name,
                "user_name": user_name,
                "access_code": access_code,
                "access_note": access_note,
            },
        )
        plain_message = (
            f"Dear {visitor_name},\n\n"
            f"You have been invited by {user_name} to visit Sunnyvale.\n\n"
            f"Access code: {access_code}\n\n"
            f"{access_note}\n\n"
            f"Thank you and we look forward to your visit!"
        )
        message = EmailMultiAlternatives(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [to_email],
        )
        message.mixed_subtype = "related"
        message.attach_alternative(html_message, "text/html")
        image = MIMEImage(qr_png, _subtype="png")
        image.add_header("Content-ID", f"<{_VISITOR_QR_CONTENT_ID}>")
        image.add_header("Content-Disposition", "inline")
        message.attach(image)
        try:
            message.send(fail_silently=False)
        except Exception:
            logger.exception(
                "Failed to send email '%s' to %s", subject, to_email
            )
            raise

    def send_checkin_notification(
        self, to_email: str, user_name: str, visitor_name: str
    ) -> None:
        subject = "Check-in notification"
        checked_in_at = timezone.localtime(timezone.now()).strftime(
            "%B %d, %Y at %I:%M %p"
        )
        self._render_and_send(
            subject,
            "checkin_notification",
            {
                "heading": "Visitor checked in",
                "user_name": user_name,
                "visitor_name": visitor_name,
                "details": [
                    {"label": "Visitor", "value": visitor_name},
                    {"label": "Checked in at", "value": checked_in_at},
                ],
            },
            to_email,
        )

    def send_checkout_notification(
        self, to_email: str, user_name: str, visitor_name: str
    ) -> None:
        subject = "Check-out notification"
        checked_out_at = timezone.localtime(timezone.now()).strftime(
            "%B %d, %Y at %I:%M %p"
        )
        self._render_and_send(
            subject,
            "checkout_notification",
            {
                "heading": "Visitor checked out",
                "user_name": user_name,
                "visitor_name": visitor_name,
                "details": [
                    {"label": "Visitor", "value": visitor_name},
                    {"label": "Checked out at", "value": checked_out_at},
                ],
            },
            to_email,
        )

    def send_delivery_notification(
        self,
        to_email: str,
        user_name: str,
        delivery_platform: str | None,
        delivery_from: str | None,
        *,
        apartment: str = "",
        block: str = "",
    ) -> None:
        subject = "Delivery notification"
        received_at = timezone.localtime(timezone.now()).strftime(
            "%B %d, %Y at %I:%M %p"
        )
        details = [{"label": "Received at", "value": received_at}]
        if apartment:
            details.insert(0, {"label": "Unit", "value": self._format_unit(apartment, block)})
        if delivery_platform:
            details.insert(
                1 if apartment else 0,
                {"label": "Delivery service", "value": delivery_platform},
            )
        if delivery_from:
            insert_at = 0
            if apartment:
                insert_at += 1
            if delivery_platform:
                insert_at += 1
            details.insert(insert_at, {"label": "Delivery from", "value": delivery_from})
        self._render_and_send(
            subject,
            "delivery_notification",
            {
                "heading": "Delivery arrived",
                "user_name": user_name,
                "details": details,
            },
            to_email,
        )

    def _format_unit(self, apartment: str, block: str) -> str:
        return f"Apt {apartment} / Block {block}" if block else f"Apt {apartment}"

    def send_household_join_request(
        self, to_email, holder_name, requester_name, apartment, block
    ) -> None:
        unit = self._format_unit(apartment, block)
        subject = "New resident request"
        self._render_and_send(
            subject,
            "household_join_request",
            {
                "heading": "New resident request",
                "holder_name": holder_name,
                "requester_name": requester_name,
                "details": [{"label": "Unit", "value": unit}],
            },
            to_email,
        )

    def send_household_creation_request(
        self, to_email, requester_name, apartment, block
    ) -> None:
        unit = self._format_unit(apartment, block)
        subject = "New household creation request"
        self._render_and_send(
            subject,
            "household_creation_request",
            {
                "heading": "New household request",
                "requester_name": requester_name,
                "details": [{"label": "Unit", "value": unit}],
            },
            to_email,
        )

    def send_household_request_approved(
        self, to_email, requester_name, apartment, block
    ) -> None:
        unit = self._format_unit(apartment, block)
        subject = "Your account is approved"
        self._render_and_send(
            subject,
            "household_request_approved",
            {
                "heading": "Account approved",
                "requester_name": requester_name,
                "unit": unit,
            },
            to_email,
        )

    def send_household_request_rejected(
        self, to_email, requester_name, apartment, block, reason
    ) -> None:
        unit = self._format_unit(apartment, block)
        subject = "Your request was rejected"
        context = {
            "heading": "Request rejected",
            "requester_name": requester_name,
            "unit": unit,
        }
        if reason:
            context["reason"] = reason
            context["reason_label"] = f"Reason: {reason}"
        self._render_and_send(
            subject,
            "household_request_rejected",
            context,
            to_email,
        )

    @staticmethod
    def _format_time_slot(
        start_time: time | None, end_time: time | None
    ) -> str:
        if not start_time and not end_time:
            return "All day"
        start = start_time.strftime("%I:%M %p") if start_time else "12:00 AM"
        end = end_time.strftime("%I:%M %p") if end_time else "11:59 PM"
        return f"{start} – {end}"

    def send_reservation_approved(
        self,
        to_email: str,
        user_name: str,
        resource_name: str,
        reservation_date: date,
        start_time: time | None,
        end_time: time | None,
    ) -> None:
        subject = f"Your {resource_name} reservation is approved"
        slot = self._format_time_slot(start_time, end_time)
        self._render_and_send(
            subject,
            "reservation_approved",
            {
                "subject": subject,
                "heading": "Reservation approved",
                "user_name": user_name,
                "resource_name": resource_name,
                "details": [
                    {"label": "Date", "value": reservation_date.strftime("%B %d, %Y")},
                    {"label": "Time", "value": slot},
                ],
            },
            to_email,
        )

    def send_reservation_rejected(
        self,
        to_email: str,
        user_name: str,
        resource_name: str,
        reservation_date: date,
        start_time: time | None,
        end_time: time | None,
        reason: str = "",
    ) -> None:
        subject = f"Your {resource_name} reservation was rejected"
        slot = self._format_time_slot(start_time, end_time)
        context = {
            "subject": subject,
            "heading": "Reservation rejected",
            "user_name": user_name,
            "resource_name": resource_name,
            "details": [
                {"label": "Date", "value": reservation_date.strftime("%B %d, %Y")},
                {"label": "Time", "value": slot},
            ],
        }
        if reason:
            context["reason"] = reason
            context["reason_label"] = f"Reason: {reason}"
        self._render_and_send(
            subject,
            "reservation_rejected",
            context,
            to_email,
        )

    def send_service_request_responded(
        self,
        to_email: str,
        requester_name: str,
        title: str,
        action: str,
        response: str,
        responder_name: str,
    ) -> None:
        accepted = action == "accept"
        subject = (
            "Your service request was accepted"
            if accepted
            else "Your service request was declined"
        )
        details = [
            {"label": "Request", "value": title},
            {"label": "Status", "value": "Accepted" if accepted else "Declined"},
            {"label": "Handled by", "value": responder_name},
        ]
        if response:
            details.append({"label": "Message", "value": response})
        self._render_and_send(
            subject,
            "service_request_responded",
            {
                "heading": "Service request update",
                "requester_name": requester_name,
                "title": title,
                "accepted": accepted,
                "status_label": "Accepted" if accepted else "Declined",
                "responder_name": responder_name,
                "response": response,
                "details": details,
            },
            to_email,
        )

    def send_visitor_arrival_notification(
        self,
        to_email: str,
        user_name: str,
        visitor_name: str,
    ) -> None:
        subject = "Visitor arrival notification"
        arrived_at = timezone.localtime(timezone.now()).strftime(
            "%B %d, %Y at %I:%M %p"
        )
        self._render_and_send(
            subject,
            "visitor_arrival_notification",
            {
                "heading": "Your visitor has arrived",
                "user_name": user_name,
                "visitor_name": visitor_name,
                "details": [
                    {"label": "Visitor", "value": visitor_name},
                    {"label": "Notified at", "value": arrived_at},
                ],
            },
            to_email,
        )

    def send_visitor_qr_sent_notification(
        self,
        to_email: str,
        user_name: str,
        visitor_name: str,
        visitor_email: str,
    ) -> None:
        subject = "Visitor QR access sent"
        sent_at = timezone.localtime(timezone.now()).strftime(
            "%B %d, %Y at %I:%M %p"
        )
        self._render_and_send(
            subject,
            "visitor_qr_sent_notification",
            {
                "heading": "Visitor QR access sent",
                "user_name": user_name,
                "visitor_name": visitor_name,
                "details": [
                    {"label": "Visitor", "value": visitor_name},
                    {"label": "Sent to", "value": visitor_email},
                    {"label": "Sent at", "value": sent_at},
                ],
            },
            to_email,
        )

    def send_email_verification_code(
        self,
        to_email: str,
        user_name: str,
        code: str,
    ) -> None:
        subject = "Verify your email"
        self._render_and_send(
            subject,
            "email_verification_code",
            {
                "heading": "Verify your email",
                "user_name": user_name,
                "code": code,
                "details": [
                    {"label": "Verification code", "value": code},
                    {
                        "label": "Expires in",
                        "value": "15 minutes",
                    },
                ],
            },
            to_email,
        )
