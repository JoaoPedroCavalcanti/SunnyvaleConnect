import pytest
from django.core import mail

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
                "link": "https://example.com/checkin/abc",
                "access_note": "The check-in link will only be accessible after your scheduled time.",
            },
            ["Alice", "Bob", "https://example.com/checkin/abc", "Check in now"],
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
    ],
)
def test_render_email_includes_expected_content(
    template_name, context, expected_fragments
):
    html, plain = render_email(template_name, context)
    for fragment in expected_fragments:
        assert fragment in html
        assert fragment in plain


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
