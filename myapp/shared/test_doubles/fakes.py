"""Reusable fakes for infrastructure interfaces."""

from shared.infrastructure.cache import ICache
from shared.infrastructure.code_generator import ICodeGenerator
from shared.infrastructure.email_sender import IEmailSender
from shared.infrastructure.qr_encoder import IQRCodeEncoder
from shared.infrastructure.string_mixer import IStringMixer


class FakeEmailSender(IEmailSender):
    def __init__(self):
        self.sent: list[dict] = []

    def send_visitor_qr_access(
        self,
        to_email,
        access_code,
        qr_png,
        user_name,
        datetime_checkin,
        datetime_checkout,
        visitor_name,
    ):
        self.sent.append({
            "kind": "visitor_qr_access",
            "to": to_email,
            "access_code": access_code,
            "qr_png": qr_png,
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

    def send_delivery_notification(
        self,
        to_email,
        user_name,
        delivery_platform,
        delivery_from,
        *,
        apartment="",
        block="",
    ):
        self.sent.append({
            "kind": "delivery",
            "to": to_email,
            "user_name": user_name,
            "platform": delivery_platform,
            "from": delivery_from,
            "apartment": apartment,
            "block": block,
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

    def send_reservation_approved(
        self,
        to_email,
        user_name,
        resource_name,
        reservation_date,
        start_time,
        end_time,
    ):
        self.sent.append({
            "kind": "reservation_approved",
            "to": to_email,
            "user_name": user_name,
            "resource_name": resource_name,
            "reservation_date": reservation_date,
            "start_time": start_time,
            "end_time": end_time,
        })

    def send_reservation_rejected(
        self,
        to_email,
        user_name,
        resource_name,
        reservation_date,
        start_time,
        end_time,
        reason="",
    ):
        self.sent.append({
            "kind": "reservation_rejected",
            "to": to_email,
            "user_name": user_name,
            "resource_name": resource_name,
            "reservation_date": reservation_date,
            "start_time": start_time,
            "end_time": end_time,
            "reason": reason,
        })

    def send_service_request_responded(
        self,
        to_email,
        requester_name,
        title,
        action,
        response,
        responder_name,
    ):
        self.sent.append({
            "kind": "service_request_responded",
            "to": to_email,
            "requester_name": requester_name,
            "title": title,
            "action": action,
            "response": response,
            "responder_name": responder_name,
        })

    def send_visitor_arrival_notification(self, to_email, user_name, visitor_name):
        self.sent.append({
            "kind": "visitor_arrival",
            "to": to_email,
            "user_name": user_name,
            "visitor_name": visitor_name,
        })


class FakeCodeGenerator(ICodeGenerator):
    def __init__(self, value: str = "12345"):
        self.value = value
        self._counter = 0

    def five_digits(self) -> str:
        return self.value

    def alphanumeric(self, length: int = 5) -> str:
        self._counter += 1
        return f"C{self._counter:04d}"[:length]


class FakeQRCodeEncoder(IQRCodeEncoder):
    def encode_png(self, payload: str) -> bytes:
        return f"qr:{payload}".encode()


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
