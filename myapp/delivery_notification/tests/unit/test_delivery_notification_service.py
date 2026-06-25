"""Unit tests for DeliveryNotificationService."""

from types import SimpleNamespace

import pytest

from delivery_notification.repositories.delivery_notification_repository import (
    IDeliveryNotificationRepository,
)
from delivery_notification.services.delivery_notification_service import (
    DeliveryNotificationService,
)
from shared.exceptions import BusinessRuleError, NotFoundError
from shared.test_doubles.fakes import FakeEmailSender
from users.repositories.user_repository import IUserRepository


pytestmark = pytest.mark.unit


class FakeDeliveryRepo(IDeliveryNotificationRepository):
    def __init__(self):
        self._items: dict[int, SimpleNamespace] = {}
        self._next_id = 1

    def list_all(self):
        return list(self._items.values())

    def get_by_id(self, pk):
        return self._items.get(int(pk))

    def create(self, data):
        item = SimpleNamespace(id=self._next_id, **{k: v for k, v in data.items() if k != "user_to_delivery"})
        self._items[self._next_id] = item
        self._next_id += 1
        return item

    def count_created_between(self, start, end):
        return 0


class FakeUserRepo(IUserRepository):
    def __init__(self):
        self._users: dict[int, SimpleNamespace] = {}

    def add(self, user):
        self._users[user.id] = user
        return user

    def list_all(self):
        return list(self._users.values())

    def list_by_role(self, role):
        return [u for u in self._users.values() if getattr(u, "role", None) == role]

    def get_by_id(self, pk):
        return self._users.get(int(pk))

    def exists_with_email(self, email):
        return any(u.email == email for u in self._users.values())

    def exists_with_username(self, username):
        return any(u.username == username for u in self._users.values())

    def exists_with_cpf(self, cpf):
        return any(getattr(u, "cpf", None) == cpf for u in self._users.values())

    def create_user(self, **k):  # not used here
        raise NotImplementedError

    def update(self, instance, data):
        for k, v in data.items():
            setattr(instance, k, v)
        return instance

    def delete(self, instance):
        self._users.pop(instance.id, None)

    def set_active(self, instance, value):
        instance.is_active = value
        return instance

    def list_admin_emails(self):
        return []

    def get_by_username(self, username):
        for u in self._users.values():
            if u.username == username:
                return u
        return None

    def check_password(self, instance, raw_password):
        return False

    def count_active(self):
        return sum(
            1 for u in self._users.values() if getattr(u, "is_active", True)
        )


@pytest.fixture
def email_sender():
    return FakeEmailSender()


@pytest.fixture
def user_repo():
    repo = FakeUserRepo()
    repo.add(SimpleNamespace(id=1, email="u@example.com", username="user1"))
    return repo


@pytest.fixture
def service(email_sender, user_repo):
    return DeliveryNotificationService(
        repository=FakeDeliveryRepo(),
        user_repository=user_repo,
        email_sender=email_sender,
    )


def test_send_creates_record_and_emails(service, email_sender, user_repo):
    user = user_repo.get_by_id(1)
    result = service.send(
        {
            "user_to_delivery": user,
            "title": "Package",
            "delivery_from": "iFood",
            "delivery_platform": "ifood",
        }
    )
    assert result is not None
    assert len(email_sender.sent) == 1
    assert email_sender.sent[0]["kind"] == "delivery"
    assert email_sender.sent[0]["to"] == "u@example.com"


def test_send_with_unknown_user_raises(service):
    with pytest.raises(NotFoundError):
        service.send(
            {
                "user_to_delivery": SimpleNamespace(id=999),
                "title": "x",
                "delivery_from": "z",
                "delivery_platform": "ifood",
            }
        )


def test_get_not_found(service):
    with pytest.raises(NotFoundError):
        service.get(123)


def test_send_with_user_without_email_raises(service, user_repo, email_sender):
    user_repo.add(SimpleNamespace(id=2, email="", username="no_email"))
    with pytest.raises(BusinessRuleError):
        service.send(
            {
                "user_to_delivery": user_repo.get_by_id(2),
                "title": "x",
                "delivery_from": "z",
                "delivery_platform": "ifood",
            }
        )
    assert email_sender.sent == []
