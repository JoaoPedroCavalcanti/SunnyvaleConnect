import pytest
from django.core import mail
from django.utils import timezone

from shared.infrastructure.email_renderer import render_email
from shared.infrastructure.email_sender import DjangoEmailSender

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "template_name,context,expected_fragments",
    [
        (
            "visitor_invite",
            {
                "heading": "You're invited to Sunnyvale",
                "visitor_name": "Alice",
                "user_name": "Bob",
                "access_code": "A1B2C",
                "access_note": "Show the QR code or tell the access code to the doorman.",
            },
            ["Alice", "Bob", "A1B2C", "Access code", "cid:visitor_qr"],
        ),
        (
            "household_request_rejected",
            {
                "heading": "Request rejected",
                "requester_name": "Carol",
                "unit": "Apt 101 / Block A",
                "reason": "invalid documents",
                "reason_label": "Reason: invalid documents",
            },
            ["Carol", "Apt 101 / Block A", "invalid documents"],
        ),
        (
            "reservation_rejected",
            {
                "subject": "Your barbecue area reservation was rejected",
                "heading": "Reservation rejected",
                "user_name": "Eve",
                "resource_name": "barbecue area",
                "details": [
                    {"label": "Date", "value": "July 4, 2026"},
                    {"label": "Time", "value": "2:00 PM – 6:00 PM"},
                ],
                "reason": "maintenance scheduled",
                "reason_label": "Reason: maintenance scheduled",
            },
            ["Eve", "barbecue area", "maintenance scheduled"],
        ),
        (
            "email_verification_code",
            {
                "heading": "Verify your email",
                "user_name": "Frank",
                "code": "654321",
                "details": [
                    {"label": "Verification code", "value": "654321"},
                    {"label": "Expires in", "value": "15 minutes"},
                ],
            },
            ["Frank", "654321", "15 minutes"],
        ),
        (
            "password_reset_code",
            {
                "heading": "Reset your password",
                "user_name": "Grace",
                "code": "112233",
                "details": [
                    {"label": "Verification code", "value": "112233"},
                    {"label": "Expires in", "value": "15 minutes"},
                ],
            },
            ["Grace", "112233", "15 minutes"],
        ),
    ],
)
def test_render_email_includes_expected_content(
    template_name, context, expected_fragments
):
    html, plain = render_email(template_name, context)
    for fragment in expected_fragments:
        assert fragment in html
        if not fragment.startswith("cid:"):
            assert fragment in plain


def test_django_email_sender_sends_visitor_qr_access_with_code_and_image():
    sender = DjangoEmailSender()
    sender.send_visitor_qr_access(
        to_email="visitor@example.com",
        access_code="C0001",
        qr_png=b"\x89PNG fake",
        user_name="Host User",
        datetime_checkin=timezone.now(),
        datetime_checkout=timezone.now(),
        visitor_name="Alice",
    )

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.subject == "Welcome to Sunnyvale"
    assert message.to == ["visitor@example.com"]
    assert "Access code: C0001" in message.body
    html_body, mime_type = message.alternatives[0]
    assert mime_type == "text/html"
    assert "C0001" in html_body
    assert "cid:visitor_qr" in html_body
    assert "data:image/png;base64," not in html_body


def test_django_email_sender_sends_html_and_plain():
    sender = DjangoEmailSender()
    sender.send_household_request_approved(
        to_email="resident@example.com",
        requester_name="Dana",
        apartment="202",
        block="B",
    )

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.subject == "Your account is approved"
    assert message.to == ["resident@example.com"]
    assert "Dana" in message.body
    assert message.alternatives
    html_body, mime_type = message.alternatives[0]
    assert mime_type == "text/html"
    assert "Dana" in html_body
    assert "Apt 202 / Block B" in html_body
