"""Unit tests for NotificationService."""

from datetime import datetime, timezone as dt_timezone
from types import SimpleNamespace

import pytest

from notifications.models import NotificationModel
from notifications.repositories.notification_repository import (
    INotificationRepository,
)
from notifications.services.notification_service import NotificationService
from shared.exceptions import BusinessRuleError, NotFoundError, PermissionDeniedError


pytestmark = pytest.mark.unit


class FakeNotificationRepo(INotificationRepository):
    def __init__(self):
        self._items = {}
        self._next_id = 1

    def list_for_user(self, user_id, *, unread_only=False):
        rows = [
            n for n in self._items.values() if n.recipient_id == user_id
        ]
        if unread_only:
            rows = [n for n in rows if n.read_at is None]
        return sorted(rows, key=lambda n: n.created_at, reverse=True)

    def count_unread(self, user_id):
        return sum(
            1
            for n in self._items.values()
            if n.recipient_id == user_id and n.read_at is None
        )

    def get_by_id(self, pk):
        return self._items.get(pk)

    def create(self, data):
        recipient = data["recipient"]
        item = SimpleNamespace(
            id=self._next_id,
            recipient=recipient,
            recipient_id=recipient.id,
            condominium_id=data.get("condominium_id"),
            type=data["type"],
            title=data["title"],
            body=data.get("body", ""),
            data=data.get("data") or {},
            read_at=None,
            created_at=datetime.now(tz=dt_timezone.utc),
            is_read=False,
        )
        self._items[self._next_id] = item
        self._next_id += 1
        return item

    def mark_read(self, instance, *, read_at):
        instance.read_at = read_at
        instance.is_read = True
        return instance

    def mark_all_read(self, user_id, *, read_at):
        updated = 0
        for n in self._items.values():
            if n.recipient_id == user_id and n.read_at is None:
                n.read_at = read_at
                n.is_read = True
                updated += 1
        return updated


def _user(pk=1, *, condominium_id=10):
    return SimpleNamespace(id=pk, condominium_id=condominium_id)


@pytest.fixture
def repo():
    return FakeNotificationRepo()


@pytest.fixture
def service(repo):
    return NotificationService(repository=repo)


class TestNotify:
    def test_creates_notification(self, service, repo):
        user = _user()
        notif = service.notify(
            user,
            type=NotificationModel.Type.DELIVERY,
            title="Package arrived",
            body="Box at lobby",
            data={"delivery_id": 9},
        )
        assert notif.id == 1
        assert notif.title == "Package arrived"
        assert notif.data == {"delivery_id": 9}
        assert notif.condominium_id == 10
        assert repo.count_unread(user.id) == 1

    def test_invalid_type_rejected(self, service):
        with pytest.raises(BusinessRuleError) as exc:
            service.notify(_user(), type="NOPE", title="x")
        assert exc.value.field == "type"

    def test_blank_title_rejected(self, service):
        with pytest.raises(BusinessRuleError) as exc:
            service.notify(
                _user(),
                type=NotificationModel.Type.GENERIC,
                title="  ",
            )
        assert exc.value.field == "title"

    def test_recipient_without_condominium_rejected(self, service):
        with pytest.raises(BusinessRuleError) as exc:
            service.notify(
                _user(condominium_id=None),
                type=NotificationModel.Type.GENERIC,
                title="Hello",
            )
        assert exc.value.field == "recipient"


class TestListAndRead:
    def test_list_only_own(self, service):
        a = _user(1)
        b = _user(2)
        service.notify(a, type="GENERIC", title="A")
        service.notify(b, type="GENERIC", title="B")
        titles = [n.title for n in service.list_for(a)]
        assert titles == ["A"]

    def test_unread_filter(self, service):
        u = _user()
        first = service.notify(u, type="GENERIC", title="One")
        service.notify(u, type="GENERIC", title="Two")
        service.mark_read(u, first.id)
        unread = list(service.list_for(u, unread_only=True))
        assert [n.title for n in unread] == ["Two"]

    def test_mark_read_idempotent(self, service):
        u = _user()
        notif = service.notify(u, type="GENERIC", title="X")
        once = service.mark_read(u, notif.id)
        twice = service.mark_read(u, notif.id)
        assert once.read_at is not None
        assert twice.read_at == once.read_at
        assert service.unread_count(u) == 0

    def test_other_user_cannot_mark_read(self, service):
        owner = _user(1)
        other = _user(2)
        notif = service.notify(owner, type="GENERIC", title="Mine")
        with pytest.raises(NotFoundError):
            service.mark_read(other, notif.id)

    def test_mark_all_read(self, service):
        u = _user()
        service.notify(u, type="GENERIC", title="1")
        service.notify(u, type="GENERIC", title="2")
        updated = service.mark_all_read(u)
        assert updated == 2
        assert service.unread_count(u) == 0

    def test_list_requires_condominium(self, service):
        with pytest.raises(PermissionDeniedError):
            service.list_for(_user(condominium_id=None))
