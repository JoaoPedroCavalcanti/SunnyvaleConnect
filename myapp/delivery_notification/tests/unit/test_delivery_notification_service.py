"""Unit tests for DeliveryNotificationService."""

from types import SimpleNamespace

import pytest

from delivery_notification.repositories.delivery_notification_repository import (
    IDeliveryNotificationRepository,
)
from delivery_notification.services.delivery_notification_service import (
    DeliveryNotificationService,
)
from households.models import Household, HouseholdMembership
from shared.exceptions import BusinessRuleError, NotFoundError
from shared.test_doubles.fakes import FakeEmailSender


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
        household = data.get("household")
        item = SimpleNamespace(
            id=self._next_id,
            household=household,
            notified_holder_name=data.get("notified_holder_name", ""),
            notified_holder_email=data.get("notified_holder_email", ""),
            **{
                k: v
                for k, v in data.items()
                if k
                not in {
                    "household",
                    "notified_holder_name",
                    "notified_holder_email",
                }
            },
        )
        self._items[self._next_id] = item
        self._next_id += 1
        return item

    def count_created_between(self, start, end):
        return 0


class FakeHouseholdRepo:
    def __init__(self):
        self._households: dict[int, SimpleNamespace] = {}
        self._next_id = 1

    def add(self, apartment, block="", status=Household.Status.ACTIVE):
        household = SimpleNamespace(
            id=self._next_id,
            apartment=apartment,
            block=block,
            status=status,
        )
        self._households[self._next_id] = household
        self._next_id += 1
        return household

    def list_all(self, status=None):
        items = list(self._households.values())
        if status:
            items = [h for h in items if h.status == status]
        return items

    def get_by_apartment_block(self, apartment, block):
        for household in self._households.values():
            if household.apartment == apartment and household.block == (block or ""):
                return household
        return None


class FakeMembershipRepo:
    def __init__(self):
        self._holders: dict[int, SimpleNamespace] = {}

    def set_holder(self, household_id, user):
        self._holders[household_id] = SimpleNamespace(
            household_id=household_id,
            user=user,
        )

    def list_active_holders_for_households(self, household_ids):
        return [
            self._holders[hid]
            for hid in household_ids
            if hid in self._holders
        ]

    def get_active_holder(self, household_id):
        return self._holders.get(household_id)

    def list_active_holders(self, household_id):
        holder = self._holders.get(household_id)
        return [holder] if holder else []


@pytest.fixture
def email_sender():
    return FakeEmailSender()


@pytest.fixture
def household_repo():
    return FakeHouseholdRepo()


@pytest.fixture
def membership_repo():
    return FakeMembershipRepo()


@pytest.fixture
def service(email_sender, household_repo, membership_repo):
    return DeliveryNotificationService(
        repository=FakeDeliveryRepo(),
        household_repository=household_repo,
        membership_repository=membership_repo,
        email_sender=email_sender,
    )


def _setup_active_household(household_repo, membership_repo, *, email="h@example.com"):
    household = household_repo.add("101", "A")
    holder = SimpleNamespace(
        id=1,
        email=email,
        username="holder1",
        full_name="Holder One",
    )
    membership_repo.set_holder(household.id, holder)
    return household, holder


def test_send_creates_record_and_emails_holder(service, email_sender, household_repo, membership_repo):
    household, holder = _setup_active_household(household_repo, membership_repo)
    result = service.send(
        {
            "apartment": household.apartment,
            "block": household.block,
            "title": "Package",
            "delivery_from": "iFood",
            "delivery_platform": "ifood",
        }
    )
    assert result is not None
    assert result.notified_holder_email == holder.email
    assert result.notified_holder_name == holder.full_name
    assert len(email_sender.sent) == 1
    assert email_sender.sent[0]["kind"] == "delivery"
    assert email_sender.sent[0]["to"] == holder.email


def test_send_unknown_apartment_raises(service):
    with pytest.raises(NotFoundError):
        service.send(
            {
                "apartment": "999",
                "block": "Z",
                "title": "x",
                "delivery_from": "z",
                "delivery_platform": "ifood",
            }
        )


def test_send_inactive_household_raises(service, household_repo, membership_repo):
    household = household_repo.add("202", "B", status=Household.Status.PENDING_ADMIN)
    membership_repo.set_holder(
        household.id,
        SimpleNamespace(id=2, email="h@x.com", username="h", full_name="H"),
    )
    with pytest.raises(BusinessRuleError):
        service.send(
            {
                "apartment": household.apartment,
                "block": household.block,
                "title": "x",
                "delivery_from": "z",
                "delivery_platform": "ifood",
            }
        )


def test_send_without_holder_raises(service, household_repo):
    household_repo.add("303", "C")
    with pytest.raises(BusinessRuleError):
        service.send(
            {
                "apartment": "303",
                "block": "C",
                "title": "x",
                "delivery_from": "z",
                "delivery_platform": "ifood",
            }
        )


def test_get_not_found(service):
    with pytest.raises(NotFoundError):
        service.get(123)


def test_send_with_holder_without_email_raises(
    service, household_repo, membership_repo, email_sender
):
    household, _ = _setup_active_household(
        household_repo, membership_repo, email=""
    )
    with pytest.raises(BusinessRuleError):
        service.send(
            {
                "apartment": household.apartment,
                "block": household.block,
                "title": "x",
                "delivery_from": "z",
                "delivery_platform": "ifood",
            }
        )
    assert email_sender.sent == []


def test_list_apartments_returns_active_units_with_holder_name(
    service, household_repo, membership_repo
):
    household, holder = _setup_active_household(household_repo, membership_repo)
    staff = SimpleNamespace(is_authenticated=True, is_staff=True, role="ADMIN")

    items = service.list_apartments(staff)

    assert len(items) == 1
    assert items[0].id == household.id
    assert items[0].apartment == "101"
    assert items[0].block == "A"
    assert items[0].holder_name == holder.full_name
    assert items[0].status == Household.Status.ACTIVE


def test_list_apartments_includes_non_archived_with_status(
    service, household_repo, membership_repo
):
    _setup_active_household(household_repo, membership_repo)
    pending = household_repo.add("404", "D", status=Household.Status.PENDING_ADMIN)
    household_repo.add("505", "E", status=Household.Status.ARCHIVED)
    staff = SimpleNamespace(is_authenticated=True, is_staff=True, role="ADMIN")

    items = service.list_apartments(staff)

    assert len(items) == 2
    statuses = {item.apartment: item.status for item in items}
    assert statuses["101"] == Household.Status.ACTIVE
    assert statuses["404"] == Household.Status.PENDING_ADMIN

