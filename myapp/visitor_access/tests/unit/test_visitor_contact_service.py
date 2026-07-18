"""Unit tests for VisitorContactService."""

from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.utils import timezone

from shared.exceptions import BusinessRuleError, NotFoundError, PermissionDeniedError
from visitor_access.repositories.visitor_contact_repository import (
    IVisitorContactRepository,
)
from visitor_access.services.visitor_access_service import IVisitorAccessService
from visitor_access.services.visitor_contact_service import VisitorContactService


pytestmark = pytest.mark.unit


class FakeContactRepo(IVisitorContactRepository):
    def __init__(self):
        self._items = {}
        self._next_id = 1

    def list_for_user(self, user_id):
        return [
            c
            for c in self._items.values()
            if c.host_user_id == user_id
        ]

    def list_all(self, *, condominium_id):
        return [
            c
            for c in self._items.values()
            if c.host_user.condominium_id == condominium_id
        ]

    def get_by_id(self, pk):
        return self._items.get(pk)

    def exists_with_name_for_user(self, user_id, name, exclude_pk=None):
        for c in self._items.values():
            if c.host_user_id != user_id:
                continue
            if exclude_pk is not None and c.id == exclude_pk:
                continue
            if c.name.casefold() == name.strip().casefold():
                return True
        return False

    def create(self, data):
        item = SimpleNamespace(id=self._next_id, **data)
        item.host_user_id = data["host_user"].id
        self._items[self._next_id] = item
        self._next_id += 1
        return item

    def update(self, instance, data):
        for k, v in data.items():
            setattr(instance, k, v)
        return instance

    def delete(self, instance):
        self._items.pop(instance.id, None)


class FakeAccessService(IVisitorAccessService):
    def __init__(self):
        self.created = []
        self._next = 1

    def list_for(self, user, period=None, status=None, is_group=None):
        return []

    def get_for(self, user, pk):
        return None

    def create(self, user, payload: dict):
        self.created.append({"user": user, "payload": payload})
        item = SimpleNamespace(
            id=self._next,
            visitor_name=payload.get("visitor_name"),
            email=payload.get("email", ""),
            host_user=payload.get("host_user") or user,
            scheduled_date=payload.get("scheduled_date"),
        )
        self._next += 1
        return item

    def update(self, user, pk, payload):
        return None

    def create_group_visits(self, user, payload: dict):
        return []

    def delete(self, user, pk):
        return None

    def validate_access(self, user, credential):
        return None

    def notify_arrival(self, user, pk):
        return None


def _user(pk=1, *, is_staff=False, role="RESIDENT", condominium_id=1):
    return SimpleNamespace(
        id=pk,
        is_staff=is_staff,
        is_authenticated=True,
        role=role,
        condominium_id=condominium_id,
        employee_types=[],
    )


@pytest.fixture
def repo():
    return FakeContactRepo()


@pytest.fixture
def access():
    return FakeAccessService()


@pytest.fixture
def service(repo, access):
    return VisitorContactService(repository=repo, visitor_access_service=access)


class TestCreate:
    def test_creates_contact(self, service):
        u = _user()
        contact = service.create(u, {"name": "João", "email": "j@x.com"})
        assert contact.name == "João"
        assert contact.email == "j@x.com"
        assert contact.host_user_id == u.id

    def test_blank_name_rejected(self, service):
        with pytest.raises(BusinessRuleError) as exc:
            service.create(_user(), {"name": "  "})
        assert exc.value.field == "name"

    def test_duplicate_name_case_insensitive(self, service):
        u = _user()
        service.create(u, {"name": "João"})
        with pytest.raises(BusinessRuleError) as exc:
            service.create(u, {"name": "joão"})
        assert exc.value.field == "name"

    def test_employee_cannot_create(self, service):
        with pytest.raises(PermissionDeniedError):
            service.create(
                _user(role="EMPLOYEE"),
                {"name": "João"},
            )


class TestUpdateDelete:
    def test_updates_name_and_email(self, service):
        u = _user()
        contact = service.create(u, {"name": "João", "email": "old@x.com"})
        updated = service.update(
            u, contact.id, {"name": "João Silva", "email": "new@x.com"}
        )
        assert updated.name == "João Silva"
        assert updated.email == "new@x.com"

    def test_other_user_cannot_get(self, service):
        owner = _user(1)
        other = _user(2)
        contact = service.create(owner, {"name": "João"})
        with pytest.raises(NotFoundError):
            service.get_for(other, contact.id)

    def test_delete(self, service, repo):
        u = _user()
        contact = service.create(u, {"name": "João"})
        service.delete(u, contact.id)
        assert repo.get_by_id(contact.id) is None


class TestSchedule:
    def test_schedules_visit_from_contact(self, service, access):
        u = _user()
        contact = service.create(u, {"name": "João", "email": "j@x.com"})
        when = timezone.now() + timedelta(days=2)
        visit = service.schedule_visit(
            u, contact.id, {"scheduled_date": when, "all_day": False}
        )
        assert visit.visitor_name == "João"
        assert access.created[0]["payload"]["visitor_name"] == "João"
        assert access.created[0]["payload"]["email"] == "j@x.com"
        assert access.created[0]["payload"]["scheduled_date"] == when
