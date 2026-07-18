"""Shared in-memory fakes for the units services unit tests."""

from types import SimpleNamespace

from condominiums.repositories.condominium_repository import ICondominiumRepository
from units.models import Unit, UnitMembership
from units.repositories.unit_membership_decision_repository import (
    IUnitMembershipDecisionRepository,
)
from units.repositories.unit_membership_repository import IUnitMembershipRepository
from units.repositories.unit_repository import IUnitRepository
from users.repositories.user_repository import IUserRepository


TEST_CONDOMINIUM_ID = 1
TEST_CONDOMINIUM_CODE = "TEST01"


def test_condominium():
    return SimpleNamespace(
        id=TEST_CONDOMINIUM_ID,
        pk=TEST_CONDOMINIUM_ID,
        code=TEST_CONDOMINIUM_CODE,
        name="Test Condo",
        slug="test-condo",
        is_active=True,
    )


def make_unit(
    pk=1,
    *,
    kind=Unit.Kind.APARTMENT,
    name="",
    apartment="101",
    block="",
    status=Unit.Status.ACTIVE,
    condominium_id=TEST_CONDOMINIUM_ID,
):
    unit = SimpleNamespace(
        id=pk,
        pk=pk,
        kind=kind,
        name=name,
        apartment=apartment,
        block=block,
        status=status,
        condominium_id=condominium_id,
        created_at=None,
    )
    unit.display_name = Unit(
        kind=kind, name=name, apartment=apartment, block=block
    ).display_name
    return unit


def make_user(
    pk=1,
    username="u",
    email="u@e.com",
    full_name="",
    cpf="",
    is_staff=False,
    is_superuser=False,
    is_active=True,
    is_authenticated=True,
    role="RESIDENT",
    condominium_id=TEST_CONDOMINIUM_ID,
    condominium=None,
):
    if condominium_id is None and condominium is None:
        condo = None
        cid = None
    elif condominium is not None:
        condo = condominium
        cid = condominium_id
    else:
        condo = test_condominium()
        cid = condominium_id
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
        is_superuser=is_superuser,
        is_active=is_active,
        is_authenticated=is_authenticated,
        role="ADMIN" if is_staff else role,
        condominium_id=cid,
        condominium=condo,
    )


def anon():
    return make_user(0, is_authenticated=False)


class FakeCondominiumRepository(ICondominiumRepository):
    def __init__(self, condominium=None):
        self._condo = condominium or test_condominium()

    def list_all(self):
        return [self._condo]

    def get_by_id(self, pk):
        if int(pk) == self._condo.id:
            return self._condo
        return None

    def get_by_code(self, code):
        normalized = (code or "").strip().upper()
        if normalized == self._condo.code.upper():
            return self._condo
        return None

    def exists_with_code(self, code):
        return self.get_by_code(code) is not None

    def create(self, data):
        self._condo = SimpleNamespace(
            id=self._condo.id,
            pk=self._condo.id,
            is_active=True,
            **data,
        )
        return self._condo

    def update(self, instance, data):
        for k, v in data.items():
            setattr(instance, k, v)
        return instance


class FakeUserRepository(IUserRepository):
    def __init__(self):
        self._users: dict[int, object] = {}
        self._next_id = 1
        self.admin_emails: list[str] = []

    def list_all(self, *, condominium_id=None):
        users = list(self._users.values())
        if condominium_id is not None:
            users = [
                u
                for u in users
                if getattr(u, "condominium_id", None) == condominium_id
            ]
        return users

    def list_by_role(self, role, *, condominium_id=None):
        return [
            u
            for u in self.list_all(condominium_id=condominium_id)
            if getattr(u, "role", None) == role
        ]

    def list_filtered(
        self, *, role=None, is_active=None, employee_type=None, condominium_id=None
    ):
        users = self.list_all(condominium_id=condominium_id)
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
        normalized = (email or "").lower().strip()
        return any(
            (u.email or "").lower().strip() == normalized for u in self._users.values()
        )

    def exists_with_username(
        self, username, *, condominium_code, exclude_id=None
    ):
        from shared.tenant import build_tenant_username

        storage_username = build_tenant_username(condominium_code, username)
        return any(
            u.username == storage_username and u.id != exclude_id
            for u in self._users.values()
        )

    def exists_with_cpf(
        self, cpf, *, condominium_id, exclude_id=None
    ):
        return any(
            u.cpf == cpf
            and getattr(u, "condominium_id", None) == condominium_id
            and u.id != exclude_id
            for u in self._users.values()
        )

    def create_user(self, **fields):
        password = fields.pop("password", "")
        user = make_user(
            self._next_id,
            username=fields.get("username", ""),
            email=fields.get("email", ""),
            condominium_id=fields.get("condominium_id", TEST_CONDOMINIUM_ID),
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

    def list_admin_emails(self, *, condominium_id):
        if self.admin_emails:
            return list(self.admin_emails)
        return [
            u.email
            for u in self._users.values()
            if getattr(u, "is_staff", False)
            and getattr(u, "condominium_id", None) == condominium_id
        ]

    def get_by_email(self, email):
        normalized = (email or "").lower().strip()
        for user in self._users.values():
            if (user.email or "").lower().strip() == normalized:
                return user
        return None

    def get_by_username(self, username, *, condominium_code=None):
        from shared.tenant import build_tenant_username

        if condominium_code:
            username = build_tenant_username(condominium_code, username)
        for u in self._users.values():
            if u.username == username:
                return u
        return None

    def check_password(self, instance, raw_password):
        return getattr(instance, "_password", None) == raw_password

    def count_active(self, *, condominium_id=None):
        users = self._users.values()
        if condominium_id is not None:
            users = [
                u for u in users if getattr(u, "condominium_id", None) == condominium_id
            ]
        return sum(1 for u in users if getattr(u, "is_active", True))


class FakeUnitRepository(IUnitRepository):
    def __init__(self):
        self._items: dict[int, object] = {}
        self._next_id = 1

    def list_all(self, status=None, *, condominium_id=None):
        items = list(self._items.values())
        if condominium_id is not None:
            items = [
                u
                for u in items
                if getattr(u, "condominium_id", None) == condominium_id
            ]
        if status:
            items = [u for u in items if u.status == status]
        return items

    def get_by_id(self, pk):
        return self._items.get(int(pk))

    def get_by_name(self, name, *, condominium_id):
        needle = (name or "").casefold()
        for u in self._items.values():
            if (
                getattr(u, "condominium_id", None) == condominium_id
                and u.kind == Unit.Kind.NAMED
                and (u.name or "").casefold() == needle
            ):
                return u
        return None

    def get_by_apartment(self, apartment, *, condominium_id):
        needle = (apartment or "").casefold()
        for u in self._items.values():
            if (
                getattr(u, "condominium_id", None) == condominium_id
                and u.kind == Unit.Kind.APARTMENT
                and (u.apartment or "").casefold() == needle
            ):
                return u
        return None

    def get_by_apartment_block(self, apartment, block, *, condominium_id):
        apt = (apartment or "").casefold()
        blk = (block or "").casefold()
        for u in self._items.values():
            if (
                getattr(u, "condominium_id", None) == condominium_id
                and u.kind == Unit.Kind.APARTMENT_BLOCK
                and (u.apartment or "").casefold() == apt
                and (u.block or "").casefold() == blk
            ):
                return u
        return None

    def create(self, data):
        unit = make_unit(
            self._next_id,
            kind=data["kind"],
            name=data.get("name", ""),
            apartment=data.get("apartment", ""),
            block=data.get("block", ""),
            status=data.get("status", Unit.Status.ACTIVE),
            condominium_id=data.get("condominium_id", TEST_CONDOMINIUM_ID),
        )
        self._items[self._next_id] = unit
        self._next_id += 1
        return unit

    def bulk_create(self, rows):
        return [self.create(row) for row in rows]

    def update(self, instance, data):
        for k, v in data.items():
            setattr(instance, k, v)
        return instance

    def delete(self, instance):
        self._items.pop(instance.id, None)


class FakeUnitMembershipRepository(IUnitMembershipRepository):
    def __init__(self):
        self._items: dict[int, UnitMembership] = {}
        self._next_id = 1

    def get_by_id(self, pk):
        return self._items.get(int(pk))

    def list_for_unit(self, unit_id):
        return [m for m in self._items.values() if m.unit_id == unit_id]

    def list_active_for_unit(self, unit_id):
        return [
            m
            for m in self._items.values()
            if m.unit_id == unit_id
            and m.status == UnitMembership.Status.ACTIVE
        ]

    def list_active_for_units(self, unit_ids):
        ids = set(unit_ids or [])
        return [
            m
            for m in self._items.values()
            if m.unit_id in ids
            and m.status == UnitMembership.Status.ACTIVE
        ]

    def list_active_owners(self, unit_id):
        return [
            m
            for m in self.list_active_for_unit(unit_id)
            if m.role == UnitMembership.Role.OWNER
        ]

    def get_active_owner(self, unit_id):
        owners = self.list_active_owners(unit_id)
        return owners[0] if owners else None

    def list_active_for_user(self, user_id):
        return [
            m
            for m in self._items.values()
            if m.user_id == user_id
            and m.status == UnitMembership.Status.ACTIVE
        ]

    def get_oldest_active_replacement(self, unit_id, excluded_user_id):
        candidates = [
            m
            for m in self.list_active_for_unit(unit_id)
            if m.user_id != excluded_user_id
            and getattr(m.user, "is_active", True)
        ]
        return min(candidates, key=lambda m: m.id, default=None)

    def list_pending_for_user(self, user_id):
        pending = {
            UnitMembership.Status.PENDING_OWNER,
            UnitMembership.Status.PENDING_ADMIN,
        }
        return [
            m
            for m in self._items.values()
            if m.user_id == user_id and m.status in pending
        ]

    def list_pending_admin(self, *, condominium_id=None):
        items = [
            m
            for m in self._items.values()
            if m.status == UnitMembership.Status.PENDING_ADMIN
        ]
        if condominium_id is not None:
            items = [
                m
                for m in items
                if getattr(m.unit, "condominium_id", None) == condominium_id
            ]
        return items

    def list_pending_owner_for_units_of(self, owner_user_id):
        owner_unit_ids = {
            m.unit_id
            for m in self._items.values()
            if m.user_id == owner_user_id
            and m.status == UnitMembership.Status.ACTIVE
            and m.role == UnitMembership.Role.OWNER
        }
        return [
            m
            for m in self._items.values()
            if m.unit_id in owner_unit_ids
            and m.status == UnitMembership.Status.PENDING_OWNER
        ]

    def get_for_user_and_unit(self, user_id, unit_id):
        for m in self._items.values():
            if m.user_id == user_id and m.unit_id == unit_id:
                return m
        return None

    def create(self, data):
        user = data["user"]
        unit = data["unit"]
        m = SimpleNamespace(
            id=self._next_id,
            pk=self._next_id,
            user=user,
            user_id=user.id,
            unit=unit,
            unit_id=unit.id,
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
        instance.status = UnitMembership.Status.LEFT
        return instance

    def delete(self, instance):
        self._items.pop(instance.id, None)


class FakeUnitMembershipDecisionRepository(
    IUnitMembershipDecisionRepository
):
    def __init__(self):
        self._items: list[object] = []
        self._next_id = 1

    def record(self, data):
        item = SimpleNamespace(
            id=self._next_id,
            pk=self._next_id,
            created_at=None,
            unit_id=data["unit"].id,
            actor_id=data["actor"].id,
            target_id=data["target"].id,
            **data,
        )
        self._items.append(item)
        self._next_id += 1
        return item

    def list_for_unit(self, unit_id):
        return [
            decision
            for decision in reversed(self._items)
            if decision.unit_id == unit_id
        ]
