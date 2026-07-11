"""Unit tests for DeliveryNotificationService."""

from types import SimpleNamespace

import pytest

from delivery_notification.repositories.delivery_notification_repository import (
    IDeliveryNotificationRepository,
)
from delivery_notification.services.delivery_notification_service import (
    DeliveryNotificationService,
)
from units.models import Unit, UnitMembership
from units.tests.unit._fakes import make_unit
from shared.exceptions import BusinessRuleError, NotFoundError
from shared.test_doubles.fakes import FakeEmailSender


pytestmark = pytest.mark.unit

TEST_CONDOMINIUM_ID = 1


class FakeDeliveryRepo(IDeliveryNotificationRepository):
    def __init__(self):
        self._items: dict[int, SimpleNamespace] = {}
        self._next_id = 1

    def list_all(self, *, condominium_id):
        return [
            i
            for i in self._items.values()
            if getattr(getattr(i, "unit", None), "condominium_id", None)
            == condominium_id
        ]

    def get_by_id(self, pk):
        return self._items.get(int(pk))

    def create(self, data):
        unit = data.get("unit")
        item = SimpleNamespace(
            id=self._next_id,
            unit=unit,
            notified_holder_name=data.get("notified_holder_name", ""),
            notified_holder_email=data.get("notified_holder_email", ""),
            **{
                k: v
                for k, v in data.items()
                if k
                not in {
                    "unit",
                    "notified_holder_name",
                    "notified_holder_email",
                }
            },
        )
        self._items[self._next_id] = item
        self._next_id += 1
        return item

    def count_created_between(self, start, end, *, condominium_id):
        return 0


class FakeUnitRepo:
    def __init__(self):
        self._units: dict[int, SimpleNamespace] = {}
        self._next_id = 1

    def add(self, apartment, block="", status=Unit.Status.ACTIVE):
        kind = Unit.Kind.APARTMENT_BLOCK if block else Unit.Kind.APARTMENT
        unit = make_unit(
            self._next_id,
            kind=kind,
            apartment=apartment,
            block=block or "",
            status=status,
            condominium_id=TEST_CONDOMINIUM_ID,
        )
        self._units[self._next_id] = unit
        self._next_id += 1
        return unit

    def list_all(self, status=None, *, condominium_id=None):
        items = list(self._units.values())
        if condominium_id is not None:
            items = [u for u in items if u.condominium_id == condominium_id]
        if status:
            items = [u for u in items if u.status == status]
        return items

    def get_by_id(self, pk):
        return self._units.get(int(pk))


class FakeMembershipRepo:
    def __init__(self):
        self._owners: dict[int, SimpleNamespace] = {}

    def set_owner(self, unit_id, user):
        self._owners[unit_id] = SimpleNamespace(
            unit_id=unit_id,
            user=user,
            role=UnitMembership.Role.OWNER,
            status=UnitMembership.Status.ACTIVE,
        )

    def list_active_for_units(self, unit_ids):
        return [
            self._owners[uid]
            for uid in unit_ids
            if uid in self._owners
        ]

    def get_active_owner(self, unit_id):
        return self._owners.get(unit_id)

    def list_active_owners(self, unit_id):
        owner = self._owners.get(unit_id)
        return [owner] if owner else []


@pytest.fixture
def email_sender():
    return FakeEmailSender()


@pytest.fixture
def unit_repo():
    return FakeUnitRepo()


@pytest.fixture
def membership_repo():
    return FakeMembershipRepo()


@pytest.fixture
def service(email_sender, unit_repo, membership_repo):
    return DeliveryNotificationService(
        repository=FakeDeliveryRepo(),
        unit_repository=unit_repo,
        membership_repository=membership_repo,
        email_sender=email_sender,
    )


def _staff():
    return SimpleNamespace(
        id=99,
        is_authenticated=True,
        is_staff=True,
        role="ADMIN",
        condominium_id=TEST_CONDOMINIUM_ID,
    )


def _setup_active_unit(unit_repo, membership_repo, *, email="h@example.com"):
    unit = unit_repo.add("101", "A")
    owner = SimpleNamespace(
        id=1,
        email=email,
        username="owner1",
        full_name="Owner One",
        condominium_id=TEST_CONDOMINIUM_ID,
    )
    membership_repo.set_owner(unit.id, owner)
    return unit, owner


def test_send_creates_record_and_emails_owner(service, email_sender, unit_repo, membership_repo):
    unit, owner = _setup_active_unit(unit_repo, membership_repo)
    result = service.send(
        _staff(),
        {
            "unit_id": unit.id,
            "title": "Package",
            "delivery_from": "iFood",
            "delivery_platform": "ifood",
        },
    )
    assert result is not None
    assert result.notified_holder_email == owner.email
    assert result.notified_holder_name == owner.full_name
    assert len(email_sender.sent) == 1
    assert email_sender.sent[0]["kind"] == "delivery"
    assert email_sender.sent[0]["to"] == owner.email


def test_send_unknown_unit_raises(service):
    with pytest.raises(NotFoundError):
        service.send(
            _staff(),
            {
                "unit_id": 999,
                "title": "x",
                "delivery_from": "z",
                "delivery_platform": "ifood",
            },
        )


def test_send_inactive_unit_raises(service, unit_repo, membership_repo):
    unit = unit_repo.add("202", "B", status=Unit.Status.ARCHIVED)
    membership_repo.set_owner(
        unit.id,
        SimpleNamespace(id=2, email="h@x.com", username="h", full_name="H"),
    )
    with pytest.raises(BusinessRuleError):
        service.send(
            _staff(),
            {
                "unit_id": unit.id,
                "title": "x",
                "delivery_from": "z",
                "delivery_platform": "ifood",
            },
        )


def test_send_without_owner_raises(service, unit_repo):
    unit = unit_repo.add("303", "C")
    with pytest.raises(BusinessRuleError):
        service.send(
            _staff(),
            {
                "unit_id": unit.id,
                "title": "x",
                "delivery_from": "z",
                "delivery_platform": "ifood",
            },
        )


def test_get_not_found(service):
    with pytest.raises(NotFoundError):
        service.get(_staff(), 123)


def test_send_with_owner_without_email_raises(
    service, unit_repo, membership_repo, email_sender
):
    unit, _ = _setup_active_unit(unit_repo, membership_repo, email="")
    with pytest.raises(BusinessRuleError):
        service.send(
            _staff(),
            {
                "unit_id": unit.id,
                "title": "x",
                "delivery_from": "z",
                "delivery_platform": "ifood",
            },
        )
    assert email_sender.sent == []


def test_list_apartments_returns_active_units_with_owner_name(
    service, unit_repo, membership_repo
):
    unit, owner = _setup_active_unit(unit_repo, membership_repo)
    staff = _staff()

    items = service.list_apartments(staff)

    assert len(items) == 1
    assert items[0].id == unit.id
    assert items[0].display_name == "Apt 101 / Block A"
    assert items[0].holder_name == owner.full_name
    assert items[0].status == Unit.Status.ACTIVE


def test_list_apartments_includes_non_archived_with_status(
    service, unit_repo, membership_repo
):
    _setup_active_unit(unit_repo, membership_repo)
    unit_repo.add("404", "D", status=Unit.Status.ACTIVE)
    unit_repo.add("505", "E", status=Unit.Status.ARCHIVED)
    staff = _staff()

    items = service.list_apartments(staff)

    assert len(items) == 2
    by_name = {item.display_name: item.status for item in items}
    assert by_name["Apt 101 / Block A"] == Unit.Status.ACTIVE
    assert by_name["Apt 404 / Block D"] == Unit.Status.ACTIVE
