"""Reusable fakes for infrastructure interfaces."""

from shared.infrastructure.code_generator import ICodeGenerator
from shared.infrastructure.email_sender import IEmailSender
from shared.infrastructure.string_mixer import IStringMixer


class FakeEmailSender(IEmailSender):
    def __init__(self):
        self.sent: list[dict] = []

    def send_visitor_invite(self, to_email, link, user_name, datetime_checkin, visitor_name):
        self.sent.append({
            "kind": "visitor_invite",
            "to": to_email,
            "link": link,
            "user_name": str(user_name),
            "visitor_name": visitor_name,
        })

    def send_checkin_notification(self, to_email, user_name, visitor_name):
        self.sent.append({
            "kind": "checkin",
            "to": to_email,
            "user_name": str(user_name),
            "visitor_name": visitor_name,
        })

    def send_checkout_notification(self, to_email, user_name, visitor_name):
        self.sent.append({
            "kind": "checkout",
            "to": to_email,
            "user_name": str(user_name),
            "visitor_name": visitor_name,
        })

    def send_delivery_notification(self, to_email, user_name, delivery_platform, delivery_from):
        self.sent.append({
            "kind": "delivery",
            "to": to_email,
            "user_name": user_name,
            "platform": delivery_platform,
            "from": delivery_from,
        })


class FakeCodeGenerator(ICodeGenerator):
    def __init__(self, value: str = "12345"):
        self.value = value

    def five_digits(self) -> str:
        return self.value


class FakeStringMixer(IStringMixer):
    """Identity mixer: mixed == raw."""

    def mix(self, value: str) -> str:
        return value

    def unmix(self, mixed: str) -> str:
        return mixed
