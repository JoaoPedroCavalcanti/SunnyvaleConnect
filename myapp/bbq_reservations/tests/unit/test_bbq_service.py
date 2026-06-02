"""Unit tests for BBQReservationService."""

from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from bbq_reservations.repositories.bbq_repository import IBBQRepository
from bbq_reservations.services.bbq_service import BBQReservationService
from households.models import HouseholdMembership
from shared.exceptions import BusinessRuleError, NotFoundError


pytestmark = pytest.mark.unit


class FakeBBQRepository(IBBQRepository):
    def __init__(self):
        self._items = []
        self._next_id = 1

    def list_all(self):
        return list(self._items)

    def get_by_id(self, pk):
        return next((i for i in self._items if i.id == pk), None)

    def exists_for_date(self, reservation_date):
        return any(
            i.reservation_date == reservation_date for i in self._items
        )

    def latest_date_for_household(self, household_id):
        dates = [
            i.reservation_date
            for i in self._items
            if getattr(i, "household", None)
            and i.household.id == household_id
        ]
        return max(dates) if dates else None

    def create(self, data):
        item = SimpleNamespace(id=self._next_id, **data)
        self._next_id += 1
        self._items.append(item)
        return item

    def update(self, instance, data):
        for k, v in data.items():
            setattr(instance, k, v)
        return instance

    def delete(self, instance):
        self._items.remove(instance)


class FakeMembershipRepo:
    """Minimal fake covering only the method bbq_service touches."""

    def __init__(self):
        self._by_user: dict[int, list] = {}

    def add(self, user_id, household, status=HouseholdMembership.Status.ACTIVE):
        m = SimpleNamespace(
            id=len(self._by_user.get(user_id, [])) + 1,
            user_id=user_id,
            household=household,
            household_id=household.id,
            status=status,
        )
        self._by_user.setdefault(user_id, []).append(m)
        return m

    def list_active_for_user(self, user_id):
        return [
            m
            for m in self._by_user.get(user_id, [])
            if m.status == HouseholdMembership.Status.ACTIVE
        ]


def _household(pk=1, apt="1101", block="A"):
    return SimpleNamespace(id=pk, apartment=apt, block=block)


def _user(pk=1, is_staff=False):
    return SimpleNamespace(id=pk, is_staff=is_staff)


def _future(days=10):
    return date.today() + timedelta(days=days)


@pytest.fixture
def fixtures():
    repo = FakeBBQRepository()
    memberships = FakeMembershipRepo()
    service = BBQReservationService(
        repository=repo, membership_repository=memberships
    )
    house = _household(1, "1101", "A")
    holder = _user(1)
    memberships.add(holder.id, house)
    return {
        "service": service,
        "repo": repo,
        "memberships": memberships,
        "house": house,
        "holder": holder,
    }


class TestCreate:
    def test_regular_user_creates_for_self(self, fixtures):
        f = fixtures
        item = f["service"].create(
            f["holder"], {"reservation_date": _future()}
        )
        assert item.reservation_user is f["holder"]
        assert item.household is f["house"]

    def test_tolerates_passing_own_id(self, fixtures):
        """Front sends ``reservation_user`` with the user's own id —
        the service must NOT reject this (regression for the 'You can
        not pass a reservation_user' error)."""
        f = fixtures
        item = f["service"].create(
            f["holder"],
            {
                "reservation_date": _future(),
                "reservation_user": f["holder"],
            },
        )
        assert item.reservation_user is f["holder"]

    def test_regular_user_cannot_pass_another_user(self, fixtures):
        f = fixtures
        other = _user(2)
        f["memberships"].add(other.id, _household(2, "1102", "A"))
        with pytest.raises(BusinessRuleError):
            f["service"].create(
                f["holder"],
                {"reservation_date": _future(), "reservation_user": other},
            )

    def test_user_without_active_household_rejected(self, fixtures):
        f = fixtures
        homeless = _user(99)
        with pytest.raises(BusinessRuleError):
            f["service"].create(homeless, {"reservation_date": _future()})

    def test_admin_must_pass_reservation_user(self, fixtures):
        f = fixtures
        with pytest.raises(BusinessRuleError):
            f["service"].create(
                _user(is_staff=True), {"reservation_date": _future()}
            )

    def test_admin_creates_for_other_using_target_household(self, fixtures):
        f = fixtures
        admin = _user(50, is_staff=True)
        target = _user(2)
        target_house = _household(2, "1102", "A")
        f["memberships"].add(target.id, target_house)
        item = f["service"].create(
            admin,
            {"reservation_date": _future(), "reservation_user": target},
        )
        assert item.household is target_house
        assert item.reservation_user is target

    def test_past_date_rejected(self, fixtures):
        f = fixtures
        with pytest.raises(BusinessRuleError):
            f["service"].create(
                f["holder"],
                {"reservation_date": date.today() - timedelta(days=1)},
            )

    def test_date_collision(self, fixtures):
        f = fixtures
        d = _future()
        f["service"].create(f["holder"], {"reservation_date": d})
        other = _user(2)
        f["memberships"].add(other.id, _household(2, "1102", "A"))
        with pytest.raises(BusinessRuleError):
            f["service"].create(other, {"reservation_date": d})

    def test_30_day_window_is_per_household(self, fixtures):
        """Two different residents of the same apartment can't both
        book within 30 days — the cool-down is per household."""
        f = fixtures
        d1 = _future(5)
        d2 = _future(15)
        f["service"].create(f["holder"], {"reservation_date": d1})
        roommate = _user(2)
        f["memberships"].add(roommate.id, f["house"])
        with pytest.raises(BusinessRuleError):
            f["service"].create(roommate, {"reservation_date": d2})

    def test_30_day_window_does_not_cross_households(self, fixtures):
        f = fixtures
        f["service"].create(f["holder"], {"reservation_date": _future(5)})
        other = _user(2)
        f["memberships"].add(other.id, _household(2, "1102", "A"))
        item = f["service"].create(
            other, {"reservation_date": _future(15)}
        )
        assert item is not None

    def test_admin_bypasses_30_day_window(self, fixtures):
        f = fixtures
        admin = _user(99, is_staff=True)
        f["service"].create(
            admin,
            {"reservation_date": _future(5), "reservation_user": f["holder"]},
        )
        item = f["service"].create(
            admin,
            {
                "reservation_date": _future(15),
                "reservation_user": f["holder"],
            },
        )
        assert item is not None


class TestGetAndDelete:
    def test_get_not_found(self, fixtures):
        with pytest.raises(NotFoundError):
            fixtures["service"].get(999)
