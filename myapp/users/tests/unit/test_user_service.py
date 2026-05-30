"""Unit tests for UserService with an in-memory fake repository."""

import pytest

from shared.exceptions import (
    BusinessRuleError,
    NotFoundError,
    PermissionDeniedError,
)
from shared.infrastructure.password_policy import DefaultPasswordPolicy
from users.repositories.user_repository import IUserRepository
from users.services.user_service import UserService


pytestmark = pytest.mark.unit


class _FakeUser:
    def __init__(
        self,
        pk,
        username="u",
        email="u@e.com",
        is_staff=False,
        is_authenticated=True,
    ):
        self.id = pk
        self.pk = pk
        self.username = username
        self.email = email
        self.first_name = ""
        self.last_name = ""
        self.is_staff = is_staff
        self.is_authenticated = is_authenticated


def _anon():
    return _FakeUser(0, is_authenticated=False)


class FakeUserRepository(IUserRepository):
    def __init__(self):
        self._users: dict[int, _FakeUser] = {}
        self._next_id = 1

    def list_all(self):
        return list(self._users.values())

    def get_by_id(self, pk):
        return self._users.get(int(pk))

    def exists_with_email(self, email):
        return any(u.email == email for u in self._users.values())

    def exists_with_username(self, username):
        return any(u.username == username for u in self._users.values())

    def create_user(self, username, password, first_name, last_name, email):
        user = _FakeUser(self._next_id, username=username, email=email)
        user.first_name = first_name
        user.last_name = last_name
        self._users[self._next_id] = user
        self._next_id += 1
        return user

    def update(self, instance, data):
        for k, v in data.items():
            setattr(instance, k, v)
        return instance

    def delete(self, instance):
        self._users.pop(instance.id, None)


@pytest.fixture
def service():
    return UserService(
        user_repository=FakeUserRepository(),
        password_policy=DefaultPasswordPolicy(),
    )


def _valid_payload(**overrides):
    data = {
        "username": "joao",
        "password": "StrongPass1!",
        "first_name": "Joao",
        "last_name": "Pedro",
        "email": "joao@example.com",
    }
    data.update(overrides)
    return data


class TestCreate:
    def test_anonymous_can_create(self, service):
        user = service.create(_anon(), _valid_payload())
        assert user.username == "joao"

    def test_admin_can_create(self, service):
        admin = _FakeUser(99, is_staff=True)
        user = service.create(admin, _valid_payload())
        assert user.username == "joao"

    def test_regular_user_cannot_create(self, service):
        with pytest.raises(PermissionDeniedError):
            service.create(_FakeUser(99), _valid_payload())

    def test_rejects_duplicate_email(self, service):
        service.create(_anon(), _valid_payload())
        with pytest.raises(BusinessRuleError) as exc:
            service.create(_anon(), _valid_payload(username="other"))
        assert exc.value.field == "email"

    def test_rejects_duplicate_username(self, service):
        service.create(_anon(), _valid_payload())
        with pytest.raises(BusinessRuleError) as exc:
            service.create(_anon(), _valid_payload(email="other@e.com"))
        assert exc.value.field == "username"

    def test_rejects_weak_password(self, service):
        with pytest.raises(BusinessRuleError) as exc:
            service.create(_anon(), _valid_payload(password="a"))
        assert exc.value.field == "password"
        assert isinstance(exc.value.message, list)


class TestGetFor:
    def test_admin_sees_anyone(self, service):
        target = service.create(_anon(), _valid_payload())
        admin = _FakeUser(99, is_staff=True)
        assert service.get_for(admin, target.id) is target

    def test_regular_user_sees_only_self(self, service):
        target = service.create(_anon(), _valid_payload())
        other = _FakeUser(99)
        with pytest.raises(NotFoundError):
            service.get_for(other, target.id)


class TestListFor:
    def test_admin_lists_all(self, service):
        service.create(_anon(), _valid_payload())
        admin = _FakeUser(99, is_staff=True)
        assert len(list(service.list_for(admin))) == 1

    def test_regular_user_lists_only_self(self, service):
        u = _FakeUser(99)
        assert list(service.list_for(u)) == [u]
