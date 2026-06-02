"""Reusable fakes for infrastructure interfaces."""

from shared.infrastructure.cache import ICache
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

    def send_household_join_request(
        self, to_email, holder_name, requester_name, apartment, block
    ):
        self.sent.append({
            "kind": "household_join_request",
            "to": to_email,
            "holder_name": holder_name,
            "requester_name": requester_name,
            "apartment": apartment,
            "block": block,
        })

    def send_household_creation_request(
        self, to_email, requester_name, apartment, block
    ):
        self.sent.append({
            "kind": "household_creation_request",
            "to": to_email,
            "requester_name": requester_name,
            "apartment": apartment,
            "block": block,
        })

    def send_household_request_approved(
        self, to_email, requester_name, apartment, block
    ):
        self.sent.append({
            "kind": "household_approved",
            "to": to_email,
            "requester_name": requester_name,
            "apartment": apartment,
            "block": block,
        })

    def send_household_request_rejected(
        self, to_email, requester_name, apartment, block, reason
    ):
        self.sent.append({
            "kind": "household_rejected",
            "to": to_email,
            "requester_name": requester_name,
            "apartment": apartment,
            "block": block,
            "reason": reason,
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


class FakeCache(ICache):
    """In-memory cache without TTL semantics (tests control eviction manually)."""

    def __init__(self):
        self.store: dict[str, object] = {}
        self.set_calls: list[tuple[str, object, int]] = []

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, ttl_seconds):
        self.store[key] = value
        self.set_calls.append((key, value, ttl_seconds))
