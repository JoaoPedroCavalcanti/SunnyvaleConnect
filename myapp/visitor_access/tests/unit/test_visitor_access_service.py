"""Unit tests for VisitorAccessService."""

from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.utils import timezone

from shared.exceptions import BusinessRuleError, NotFoundError
from shared.test_doubles.fakes import (
    FakeCodeGenerator,
    FakeEmailSender,
    FakeStringMixer,
)
from visitor_access.repositories.visitor_access_repository import (
    IVisitorAccessRepository,
)
from visitor_access.services.visitor_access_service import VisitorAccessService


pytestmark = pytest.mark.unit


class FakeVisitorAccessRepo(IVisitorAccessRepository):
    def __init__(self):
        self._items: dict[int, SimpleNamespace] = {}
        self._next_id = 1

    def list_all(self):
        return list(self._items.values())

    def list_for_user(self, user_id):
        return [i for i in self._items.values() if getattr(i.host_user, "id", None) == user_id]

    def get_by_id(self, pk):
        return self._items.get(int(pk))

    def create(self, data):
        defaults = {
            "checkout_date_time": None,
            "checkin_code": "",
            "checkout_code": "",
            "link_checkin": "",
            "link_checkout": "",
            "status": "Scheduled",
        }
        defaults.update(data)
        item = SimpleNamespace(id=self._next_id, **defaults)
        item.host_user_id = getattr(data.get("host_user"), "id", None)
        self._items[self._next_id] = item
        self._next_id += 1
        return item

    def save(self, instance):
        self._items[instance.id] = instance
        return instance

    def update(self, instance, data):
        for k, v in data.items():
            setattr(instance, k, v)
        return instance

    def delete(self, instance):
        self._items.pop(instance.id, None)


@pytest.fixture
def email_sender():
    return FakeEmailSender()


@pytest.fixture
def service(email_sender):
    return VisitorAccessService(
        repository=FakeVisitorAccessRepo(),
        email_sender=email_sender,
        code_generator=FakeCodeGenerator("99999"),
        string_mixer=FakeStringMixer(),
        visitor_access_base_url="http://test/visitor_access",
    )


def _user(pk=1, is_staff=False):
    return SimpleNamespace(id=pk, is_staff=is_staff)


def _payload(**overrides):
    data = {
        "visitor_name": "Guest",
        "email": "v@example.com",
        "scheduled_date": timezone.now() + timedelta(days=1),
    }
    data.update(overrides)
    return data


class TestCreate:
    def test_regular_user_creates_for_self(self, service, email_sender):
        u = _user()
        item = service.create(u, _payload())
        assert item.host_user is u
        assert "/checkin/" in item.link_checkin
        # invite email sent
        assert any(s["kind"] == "visitor_invite" for s in email_sender.sent)

    def test_regular_user_cannot_pass_host_user(self, service):
        with pytest.raises(BusinessRuleError):
            service.create(_user(1), _payload(host_user=_user(2)))

    def test_admin_must_pass_host_user(self, service):
        with pytest.raises(BusinessRuleError):
            service.create(_user(is_staff=True), _payload())

    def test_past_date_rejected(self, service):
        with pytest.raises(BusinessRuleError):
            service.create(
                _user(),
                _payload(scheduled_date=timezone.now() - timedelta(days=1)),
            )


class TestCheckin:
    def test_checkin_inside_window(self, service, email_sender):
        u = _user(1)
        item = service.create(u, _payload())
        # rewind the window so we're inside it
        item.checkin_date_time = timezone.now() - timedelta(minutes=5)
        item.checkout_date_time = timezone.now() + timedelta(hours=2)

        result = service.checkin(str(item.id))
        assert result == {"checkin_code": "99999"}
        assert item.status == "Checked-in"
        assert any(s["kind"] == "checkin" for s in email_sender.sent)

    def test_checkin_outside_window(self, service):
        u = _user(1)
        item = service.create(u, _payload(scheduled_date=timezone.now() + timedelta(days=2)))
        result = service.checkin(str(item.id))
        assert isinstance(result, str)
        assert "scheduled time" in result

    def test_checkin_after_checkout_blocked(self, service):
        u = _user(1)
        item = service.create(u, _payload())
        item.status = "Checked-out"
        with pytest.raises(BusinessRuleError):
            service.checkin(str(item.id))


class TestCheckout:
    def test_checkout_blocked_if_still_scheduled(self, service):
        u = _user(1)
        item = service.create(u, _payload())
        with pytest.raises(BusinessRuleError):
            service.checkout(str(item.id))

    def test_checkout_after_checkin(self, service, email_sender):
        u = _user(1)
        item = service.create(u, _payload(scheduled_date=timezone.now() + timedelta(hours=2)))
        item.status = "Checked-in"
        item.checkin_code = "11111"

        result = service.checkout(str(item.id))
        assert result == {"checkout_code": "99999"}
        assert item.status == "Checked-out"
        assert any(s["kind"] == "checkout" for s in email_sender.sent)


class TestDelete:
    def test_cannot_delete_past(self, service):
        u = _user(1)
        item = service.create(u, _payload())
        item.scheduled_date = timezone.now() - timedelta(hours=1)
        with pytest.raises(BusinessRuleError):
            service.delete(u, item.id)

    def test_delete_future_ok(self, service):
        u = _user(1)
        item = service.create(u, _payload())
        service.delete(u, item.id)
        with pytest.raises(NotFoundError):
            service.get_for(u, item.id)
