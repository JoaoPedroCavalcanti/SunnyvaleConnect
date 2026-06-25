"""Unit tests for VisitorGroupService."""

from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.utils import timezone

from shared.exceptions import BusinessRuleError, NotFoundError
from visitor_access.repositories.visitor_group_repository import (
    IVisitorGroupRepository,
)
from visitor_access.services.visitor_access_service import IVisitorAccessService
from visitor_access.services.visitor_group_service import VisitorGroupService


pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------- #
# fakes                                                                  #
# ---------------------------------------------------------------------- #
class _MembersManager:
    """Mimics group.members.all() and group.members.count()."""

    def __init__(self, items: list):
        self._items = items

    def all(self):
        return list(self._items)

    def count(self):
        return len(self._items)


class FakeVisitorGroupRepo(IVisitorGroupRepository):
    def __init__(self):
        self._groups: dict[int, SimpleNamespace] = {}
        self._members: dict[int, list[SimpleNamespace]] = {}
        self._next_group_id = 1
        self._next_member_id = 1

    # bookkeeping
    def _attach_members(self, group):
        group.members = _MembersManager(self._members.get(group.id, []))
        return group

    # IVisitorGroupRepository
    def list_for_user(self, user_id):
        return [
            self._attach_members(g)
            for g in self._groups.values()
            if g.host_user.id == user_id
        ]

    def list_all(self):
        return [self._attach_members(g) for g in self._groups.values()]

    def get_by_id(self, pk):
        g = self._groups.get(int(pk))
        return self._attach_members(g) if g else None

    def exists_with_name_for_user(self, user_id, name, exclude_pk=None):
        for g in self._groups.values():
            if (
                g.host_user.id == user_id
                and g.name == name
                and (exclude_pk is None or g.id != exclude_pk)
            ):
                return True
        return False

    def create(self, data):
        group = SimpleNamespace(
            id=self._next_group_id,
            host_user=data["host_user"],
            host_user_id=data["host_user"].id,
            name=data["name"],
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )
        self._groups[self._next_group_id] = group
        self._members.setdefault(self._next_group_id, [])
        self._next_group_id += 1
        return group

    def update(self, instance, data):
        for k, v in data.items():
            setattr(instance, k, v)
        return instance

    def delete(self, instance):
        self._groups.pop(instance.id, None)
        self._members.pop(instance.id, None)

    def list_members(self, group_id):
        return list(self._members.get(group_id, []))

    def replace_members(self, group, members):
        self._members[group.id] = []
        return self.add_members(group, members)

    def add_members(self, group, members):
        for m in members:
            self._members.setdefault(group.id, []).append(
                SimpleNamespace(
                    id=self._next_member_id,
                    name=m["name"],
                    email=m.get("email", "") or "",
                )
            )
            self._next_member_id += 1
        return list(self._members[group.id])


class FakeAccessService(IVisitorAccessService):
    """Captures `create` calls so we can assert how the group scheduled."""

    def __init__(self):
        self.created: list[dict] = []
        self._next = 1

    def list_for(self, user, period=None, status=None, is_group=None):  # pragma: no cover - not used here
        return []

    def get_for(self, user, pk):  # pragma: no cover - not used here
        return None

    def create(self, user, payload: dict):
        self.created.append({"user": user, "payload": payload})
        group = payload.get("visitor_group")
        item = SimpleNamespace(
            id=self._next,
            host_user=user,
            visitor_name=payload["visitor_name"],
            email=payload.get("email", ""),
            scheduled_date=payload.get("scheduled_date"),
            all_day=payload.get("all_day", False),
            visitor_group=group,
            visitor_group_id=getattr(group, "id", None),
        )
        self._next += 1
        return item

    def delete(self, user, pk):  # pragma: no cover
        return None

    def checkin(self, mixed_link):  # pragma: no cover
        return None

    def checkout(self, mixed_link):  # pragma: no cover
        return None

    def notify_arrival(self, user, pk):  # pragma: no cover
        return None


# ---------------------------------------------------------------------- #
# fixtures                                                               #
# ---------------------------------------------------------------------- #
@pytest.fixture
def repo():
    return FakeVisitorGroupRepo()


@pytest.fixture
def access():
    return FakeAccessService()


@pytest.fixture
def service(repo, access):
    return VisitorGroupService(repository=repo, visitor_access_service=access)


def _user(pk=1, is_staff=False, role=None):
    return SimpleNamespace(
        id=pk,
        is_staff=is_staff,
        is_authenticated=True,
        role=role or ("ADMIN" if is_staff else "RESIDENT"),
        employee_types=[],
    )


# ---------------------------------------------------------------------- #
# tests                                                                  #
# ---------------------------------------------------------------------- #
class TestCreate:
    def test_creates_with_members(self, service):
        u = _user()
        group = service.create(
            u,
            {
                "name": "Família Pai",
                "members": [
                    {"name": "João", "email": "j@x.com"},
                    {"name": "Maria", "email": "m@x.com"},
                ],
            },
        )
        assert group.name == "Família Pai"
        assert group.members.count() == 2

    def test_blank_name_rejected(self, service):
        with pytest.raises(BusinessRuleError):
            service.create(_user(), {"name": "  ", "members": []})

    def test_duplicate_name_rejected(self, service):
        u = _user()
        service.create(u, {"name": "Família Pai", "members": []})
        with pytest.raises(BusinessRuleError):
            service.create(u, {"name": "Família Pai", "members": []})

    def test_member_without_name_rejected(self, service):
        with pytest.raises(BusinessRuleError):
            service.create(
                _user(),
                {"name": "G", "members": [{"name": "", "email": "x@y.com"}]},
            )


class TestUpdate:
    def test_replaces_members(self, service):
        u = _user()
        group = service.create(
            u,
            {"name": "G", "members": [{"name": "A", "email": ""}]},
        )
        updated = service.update(
            u,
            group.id,
            {"members": [{"name": "B"}, {"name": "C"}]},
        )
        names = [m.name for m in updated.members.all()]
        assert names == ["B", "C"]

    def test_renames_group(self, service):
        u = _user()
        group = service.create(u, {"name": "Old", "members": []})
        updated = service.update(u, group.id, {"name": "New"})
        assert updated.name == "New"

    def test_rename_collision(self, service):
        u = _user()
        service.create(u, {"name": "A", "members": []})
        g = service.create(u, {"name": "B", "members": []})
        with pytest.raises(BusinessRuleError):
            service.update(u, g.id, {"name": "A"})


class TestVisibility:
    def test_other_user_cannot_get(self, service):
        owner = _user(1)
        outsider = _user(2)
        group = service.create(owner, {"name": "G", "members": []})
        with pytest.raises(NotFoundError):
            service.get_for(outsider, group.id)

    def test_admin_sees_anyone(self, service):
        owner = _user(1)
        admin = _user(99, is_staff=True)
        group = service.create(owner, {"name": "G", "members": []})
        assert service.get_for(admin, group.id).id == group.id


class TestSchedule:
    def test_schedules_single_visit_for_whole_group(self, service, access):
        """schedule_visit produces one VisitorAccess row, not N."""
        u = _user(1)
        group = service.create(
            u,
            {
                "name": "Família Pai",
                "members": [
                    {"name": "A", "email": "a@x.com"},
                    {"name": "B", "email": "b@x.com"},
                ],
            },
        )
        when = timezone.now() + timedelta(days=1)
        result = service.schedule_visit(
            u,
            group.id,
            {"scheduled_date": when, "all_day": False},
        )

        assert len(access.created) == 1
        call = access.created[0]
        assert call["payload"]["visitor_group"] is group
        assert call["payload"]["visitor_name"] == "Família Pai"
        assert call["payload"]["email"] == ""
        assert call["payload"]["scheduled_date"] == when
        # returns the single visit, not a list
        assert result.visitor_group is group
        assert result.visitor_name == "Família Pai"

    def test_schedule_all_day_propagates(self, service, access):
        u = _user(1)
        group = service.create(
            u, {"name": "G", "members": [{"name": "A", "email": ""}]}
        )
        when = timezone.now() + timedelta(days=1)
        service.schedule_visit(
            u, group.id, {"scheduled_date": when, "all_day": True}
        )
        assert access.created[0]["payload"]["all_day"] is True
        # all_day must drop checkout_date_time so the access service decides it
        assert "checkout_date_time" not in access.created[0]["payload"]

    def test_empty_group_blocked(self, service):
        u = _user(1)
        group = service.create(u, {"name": "G", "members": []})
        with pytest.raises(BusinessRuleError):
            service.schedule_visit(
                u, group.id, {"scheduled_date": timezone.now() + timedelta(days=1)}
            )

    def test_admin_schedules_in_owners_name(self, service, access):
        owner = _user(1)
        admin = _user(99, is_staff=True)
        group = service.create(owner, {"name": "G", "members": [{"name": "A"}]})
        service.schedule_visit(
            admin,
            group.id,
            {"scheduled_date": timezone.now() + timedelta(days=1)},
        )
        assert access.created[0]["user"] is owner
