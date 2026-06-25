"""Shared in-memory fakes for the household-related services unit tests."""

from types import SimpleNamespace

from households.models import Household, HouseholdMembership
from households.repositories.dependent_repository import IDependentRepository
from households.repositories.household_repository import IHouseholdRepository
from households.repositories.membership_decision_repository import (
    IMembershipDecisionRepository,
)
from households.repositories.membership_repository import IMembershipRepository
from users.repositories.user_repository import IUserRepository


def make_user(
    pk=1,
    username="u",
    email="u@e.com",
    full_name="",
    cpf="",
    is_staff=False,
    is_active=True,
    is_authenticated=True,
    role="RESIDENT",
):
    return SimpleNamespace(
        id=pk,
        pk=pk,
        username=username,
        email=email,
        full_name=full_name,
        cpf=cpf,
        phone="",
        birth_date=None,
        apartment="",
        block="",
        photo=None,
        is_staff=is_staff,
        is_active=is_active,
        is_authenticated=is_authenticated,
        role="ADMIN" if is_staff else role,
    )


def anon():
    return make_user(0, is_authenticated=False)


class FakeUserRepository(IUserRepository):
    def __init__(self):
        self._users: dict[int, object] = {}
        self._next_id = 1
        self.admin_emails: list[str] = []

    def list_all(self):
        return list(self._users.values())

    def list_by_role(self, role):
        return [u for u in self._users.values() if getattr(u, "role", None) == role]

    def list_filtered(self, *, role=None, is_active=None, employee_type=None):
        users = list(self._users.values())
        if role is not None:
            users = [u for u in users if getattr(u, "role", None) == role]
        if is_active is not None:
            users = [u for u in users if getattr(u, "is_active", True) == is_active]
        if employee_type is not None:
            users = [
                u
                for u in users
                if employee_type in (getattr(u, "employee_types", None) or [])
            ]
        return users

    def get_by_id(self, pk):
        return self._users.get(int(pk))

    def exists_with_email(self, email):
        return any(u.email == email for u in self._users.values())

    def exists_with_username(self, username):
        return any(u.username == username for u in self._users.values())

    def exists_with_cpf(self, cpf):
        return any(u.cpf == cpf for u in self._users.values())

    def create_user(self, **fields):
        password = fields.pop("password", "")
        user = make_user(
            self._next_id,
            username=fields.get("username", ""),
            email=fields.get("email", ""),
        )
        for k, v in fields.items():
            setattr(user, k, v)
        user._password = password
        self._users[self._next_id] = user
        self._next_id += 1
        return user

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
        return list(self.admin_emails)

    def get_by_username(self, username):
        for u in self._users.values():
            if u.username == username:
                return u
        return None

    def check_password(self, instance, raw_password):
        return getattr(instance, "_password", None) == raw_password

    def count_active(self):
        return sum(
            1 for u in self._users.values() if getattr(u, "is_active", True)
        )


class FakeHouseholdRepository(IHouseholdRepository):
    def __init__(self):
        self._items: dict[int, Household] = {}
        self._next_id = 1

    def list_all(self, status=None):
        items = list(self._items.values())
        if status:
            items = [h for h in items if h.status == status]
        return items

    def get_by_id(self, pk):
        return self._items.get(int(pk))

    def get_by_apartment_block(self, apartment, block):
        for h in self._items.values():
            if h.apartment == apartment and h.block == block:
                return h
        return None

    def search(self, apartment, block):
        results = []
        for h in self._items.values():
            if h.status == Household.Status.ARCHIVED:
                continue
            if apartment and h.apartment.lower() != apartment.lower():
                continue
            if block and h.block.lower() != block.lower():
                continue
            results.append(h)
        return results

    def create(self, data):
        h = SimpleNamespace(
            id=self._next_id,
            pk=self._next_id,
            apartment=data["apartment"],
            block=data.get("block", ""),
            status=data.get("status", Household.Status.PENDING_ADMIN),
        )
        self._items[self._next_id] = h
        self._next_id += 1
        return h

    def update(self, instance, data):
        for k, v in data.items():
            setattr(instance, k, v)
        return instance

    def delete(self, instance):
        self._items.pop(instance.id, None)


class FakeMembershipRepository(IMembershipRepository):
    def __init__(self):
        self._items: dict[int, HouseholdMembership] = {}
        self._next_id = 1

    def get_by_id(self, pk):
        return self._items.get(int(pk))

    def list_for_household(self, household_id):
        return [m for m in self._items.values() if m.household_id == household_id]

    def list_active_for_household(self, household_id):
        return [
            m
            for m in self._items.values()
            if m.household_id == household_id
            and m.status == HouseholdMembership.Status.ACTIVE
        ]

    def list_active_for_households(self, household_ids):
        ids = set(household_ids or [])
        return [
            m
            for m in self._items.values()
            if m.household_id in ids
            and m.status == HouseholdMembership.Status.ACTIVE
        ]

    def list_active_holders(self, household_id):
        return [
            m
            for m in self.list_active_for_household(household_id)
            if m.role == HouseholdMembership.Role.HOLDER
        ]

    def list_active_for_user(self, user_id):
        return [
            m
            for m in self._items.values()
            if m.user_id == user_id
            and m.status == HouseholdMembership.Status.ACTIVE
        ]

    def list_pending_for_user(self, user_id):
        pending = {
            HouseholdMembership.Status.PENDING_HOLDER,
            HouseholdMembership.Status.PENDING_ADMIN,
        }
        return [
            m
            for m in self._items.values()
            if m.user_id == user_id and m.status in pending
        ]

    def list_pending_admin(self):
        return [
            m
            for m in self._items.values()
            if m.status == HouseholdMembership.Status.PENDING_ADMIN
        ]

    def list_pending_holder_for_houses_of(self, holder_user_id):
        holder_household_ids = {
            m.household_id
            for m in self._items.values()
            if m.user_id == holder_user_id
            and m.status == HouseholdMembership.Status.ACTIVE
            and m.role == HouseholdMembership.Role.HOLDER
        }
        return [
            m
            for m in self._items.values()
            if m.household_id in holder_household_ids
            and m.status == HouseholdMembership.Status.PENDING_HOLDER
        ]

    def get_for_user_and_household(self, user_id, household_id):
        for m in self._items.values():
            if m.user_id == user_id and m.household_id == household_id:
                return m
        return None

    def create(self, data):
        user = data["user"]
        household = data["household"]
        m = SimpleNamespace(
            id=self._next_id,
            pk=self._next_id,
            user=user,
            user_id=user.id,
            household=household,
            household_id=household.id,
            role=data["role"],
            status=data["status"],
            joined_at=None,
            left_at=None,
        )
        self._items[self._next_id] = m
        self._next_id += 1
        return m

    def update(self, instance, data):
        for k, v in data.items():
            setattr(instance, k, v)
        return instance

    def soft_leave(self, instance):
        instance.status = HouseholdMembership.Status.LEFT
        return instance

    def delete(self, instance):
        self._items.pop(instance.id, None)


class FakeMembershipDecisionRepository(IMembershipDecisionRepository):
    def __init__(self):
        self._items: list = []
        self._next_id = 1

    def record(self, data):
        actor = data.get("actor")
        target = data.get("target")
        household = data.get("household")
        d = SimpleNamespace(
            id=self._next_id,
            household=household,
            household_id=getattr(household, "id", None),
            household_apartment=data.get("household_apartment", ""),
            household_block=data.get("household_block", ""),
            actor=actor,
            actor_id=getattr(actor, "id", None),
            actor_username=data.get("actor_username", ""),
            actor_full_name=data.get("actor_full_name", ""),
            target=target,
            target_id=getattr(target, "id", None),
            target_username=data.get("target_username", ""),
            target_full_name=data.get("target_full_name", ""),
            target_email=data.get("target_email", ""),
            action=data["action"],
            reason=data.get("reason", ""),
            created_at=None,
        )
        self._items.append(d)
        self._next_id += 1
        return d

    def list_for_household(self, household_id):
        return [
            d
            for d in reversed(self._items)
            if d.household_id == household_id
        ]


class FakeDependentRepository(IDependentRepository):
    def __init__(self):
        self._items: dict[int, object] = {}
        self._next_id = 1

    def list_for_household(self, household_id):
        return [
            d
            for d in self._items.values()
            if d.household_id == household_id and d.is_active
        ]

    def get_by_id(self, pk):
        return self._items.get(int(pk))

    def exists_active_with_cpf(self, cpf):
        if not cpf:
            return False
        return any(
            d.cpf == cpf and d.is_active for d in self._items.values()
        )

    def create(self, data):
        household = data.pop("household")
        d = SimpleNamespace(
            id=self._next_id,
            household=household,
            household_id=household.id,
            full_name=data.get("full_name", ""),
            birth_date=data.get("birth_date"),
            cpf=data.get("cpf", ""),
            relationship=data.get("relationship", ""),
            is_active=True,
        )
        self._items[self._next_id] = d
        self._next_id += 1
        return d

    def update(self, instance, data):
        for k, v in data.items():
            setattr(instance, k, v)
        return instance

    def soft_delete(self, instance):
        instance.is_active = False
        return instance
