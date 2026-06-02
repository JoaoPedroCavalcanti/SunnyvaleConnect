"""Unit tests for BBQReservationService."""

from datetime import date, time, timedelta
from types import SimpleNamespace

import pytest

from bbq_reservations.models import BBQReservationModel
from bbq_reservations.repositories.bbq_repository import IBBQRepository
from bbq_reservations.services.bbq_service import BBQReservationService
from households.models import HouseholdMembership
from shared.exceptions import (
    BusinessRuleError,
    NotFoundError,
    PermissionDeniedError,
)


pytestmark = pytest.mark.unit


class FakeBBQRepository(IBBQRepository):
    def __init__(self):
        self._items = []
        self._next_id = 1

    def list_all(self):
        return list(self._items)

    def get_by_id(self, pk):
        return next((i for i in self._items if i.id == pk), None)

    def list_for_date(self, reservation_date):
        return [
            i
            for i in self._items
            if i.reservation_date == reservation_date
            and i.status == BBQReservationModel.Status.APPROVED
        ]

    def latest_date_for_household(self, household_id):
        dates = [
            i.reservation_date
            for i in self._items
            if getattr(i, "household", None)
            and i.household.id == household_id
            and i.status == BBQReservationModel.Status.APPROVED
        ]
        return max(dates) if dates else None

    def create(self, data):
        household = data.get("household")
        item = SimpleNamespace(
            id=self._next_id,
            start_time=data.get("start_time"),
            end_time=data.get("end_time"),
            household_id=household.id if household else None,
            **{k: v for k, v in data.items() if k not in (
                "start_time", "end_time"
            )},
        )
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
    admin = _user(99, is_staff=True)
    memberships.add(holder.id, house)

    def book_approved(target_user, **payload):
        """Shortcut: admin creates -> immediately APPROVED.
        Used by tests that need an APPROVED booking as setup."""
        return service.create(
            admin, {**payload, "reservation_user": target_user}
        )

    return {
        "service": service,
        "repo": repo,
        "memberships": memberships,
        "house": house,
        "holder": holder,
        "admin": admin,
        "book_approved": book_approved,
    }


class TestCreate:
    def test_regular_user_creates_for_self(self, fixtures):
        f = fixtures
        item = f["service"].create(
            f["holder"], {"reservation_date": _future()}
        )
        assert item.reservation_user is f["holder"]
        assert item.household is f["house"]
        assert item.status == BBQReservationModel.Status.PENDING

    def test_admin_creation_is_auto_approved(self, fixtures):
        f = fixtures
        item = f["book_approved"](f["holder"], reservation_date=_future())
        assert item.status == BBQReservationModel.Status.APPROVED

    def test_pending_does_not_block_other_pending(self, fixtures):
        """Two morador-created (PENDING) bookings on the same day are
        allowed — the admin will decide which one wins on approval."""
        f = fixtures
        d = _future()
        f["service"].create(f["holder"], {"reservation_date": d})
        other = _user(2)
        f["memberships"].add(other.id, _household(2, "1102", "A"))
        item = f["service"].create(other, {"reservation_date": d})
        assert item is not None
        assert item.status == BBQReservationModel.Status.PENDING

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

    def test_full_day_collides_with_full_day(self, fixtures):
        f = fixtures
        d = _future()
        f["book_approved"](f["holder"], reservation_date=d)
        other = _user(2)
        f["memberships"].add(other.id, _household(2, "1102", "A"))
        with pytest.raises(BusinessRuleError):
            f["book_approved"](other, reservation_date=d)

    def test_full_day_collides_with_any_slot(self, fixtures):
        f = fixtures
        d = _future()
        f["book_approved"](f["holder"], reservation_date=d)
        other = _user(2)
        f["memberships"].add(other.id, _household(2, "1102", "A"))
        with pytest.raises(BusinessRuleError):
            f["book_approved"](
                other,
                reservation_date=d,
                start_time=time(14, 0),
                end_time=time(18, 0),
            )

    def test_adjacent_slots_are_allowed(self, fixtures):
        f = fixtures
        d = _future()
        f["book_approved"](
            f["holder"],
            reservation_date=d,
            start_time=time(12, 0),
            end_time=time(18, 0),
        )
        other = _user(2)
        f["memberships"].add(other.id, _household(2, "1102", "A"))
        item = f["book_approved"](
            other,
            reservation_date=d,
            start_time=time(18, 0),
            end_time=time(22, 0),
        )
        assert item.start_time == time(18, 0)

    def test_overlapping_slots_collide(self, fixtures):
        f = fixtures
        d = _future()
        f["book_approved"](
            f["holder"],
            reservation_date=d,
            start_time=time(12, 0),
            end_time=time(18, 0),
        )
        other = _user(2)
        f["memberships"].add(other.id, _household(2, "1102", "A"))
        with pytest.raises(BusinessRuleError):
            f["book_approved"](
                other,
                reservation_date=d,
                start_time=time(17, 0),
                end_time=time(22, 0),
            )

    def test_open_end_blocks_late_window(self, fixtures):
        """Approved booking with only start_time (15h → end of day)
        must block any later same-day slot."""
        f = fixtures
        d = _future()
        f["book_approved"](
            f["holder"], reservation_date=d, start_time=time(15, 0)
        )
        other = _user(2)
        f["memberships"].add(other.id, _household(2, "1102", "A"))
        with pytest.raises(BusinessRuleError):
            f["book_approved"](
                other,
                reservation_date=d,
                start_time=time(20, 0),
                end_time=time(22, 0),
            )

    def test_open_end_allows_earlier_window(self, fixtures):
        f = fixtures
        d = _future()
        f["book_approved"](
            f["holder"], reservation_date=d, start_time=time(15, 0)
        )
        other = _user(2)
        f["memberships"].add(other.id, _household(2, "1102", "A"))
        item = f["book_approved"](
            other,
            reservation_date=d,
            start_time=time(8, 0),
            end_time=time(15, 0),
        )
        assert item is not None

    def test_invalid_slot_start_after_end(self, fixtures):
        f = fixtures
        with pytest.raises(BusinessRuleError):
            f["service"].create(
                f["holder"],
                {
                    "reservation_date": _future(),
                    "start_time": time(18, 0),
                    "end_time": time(12, 0),
                },
            )

    def test_30_day_window_is_per_household(self, fixtures):
        """Two different residents of the same apartment can't both
        book within 30 days — the cool-down is per household. Only
        APPROVED bookings count toward this window."""
        f = fixtures
        f["book_approved"](f["holder"], reservation_date=_future(5))
        roommate = _user(2)
        f["memberships"].add(roommate.id, f["house"])
        with pytest.raises(BusinessRuleError):
            f["service"].create(roommate, {"reservation_date": _future(15)})

    def test_30_day_window_does_not_cross_households(self, fixtures):
        f = fixtures
        f["book_approved"](f["holder"], reservation_date=_future(5))
        other = _user(2)
        f["memberships"].add(other.id, _household(2, "1102", "A"))
        item = f["service"].create(
            other, {"reservation_date": _future(15)}
        )
        assert item is not None

    def test_pending_does_not_count_toward_cooldown(self, fixtures):
        """A PENDING booking from the same apartment must not block
        another booking from being created — only APPROVED counts."""
        f = fixtures
        f["service"].create(f["holder"], {"reservation_date": _future(5)})
        roommate = _user(2)
        f["memberships"].add(roommate.id, f["house"])
        item = f["service"].create(
            roommate, {"reservation_date": _future(15)}
        )
        assert item is not None

    def test_admin_bypasses_30_day_window(self, fixtures):
        f = fixtures
        # Admin books day 5 (auto-APPROVED, counts toward cooldown)
        # then books day 15 — admins skip the 30-day check.
        # But since they're APPROVED back-to-back, the second one would
        # normally collide with the first via cooldown rule. The bypass
        # makes it allowed.
        d1 = _future(5)
        d2 = _future(15)
        f["book_approved"](f["holder"], reservation_date=d1)
        item = f["book_approved"](f["holder"], reservation_date=d2)
        assert item is not None


class TestApproveReject:
    def test_only_admin_can_approve(self, fixtures):
        f = fixtures
        item = f["service"].create(
            f["holder"], {"reservation_date": _future()}
        )
        with pytest.raises(PermissionDeniedError):
            f["service"].approve(f["holder"], item.id)

    def test_only_admin_can_reject(self, fixtures):
        f = fixtures
        item = f["service"].create(
            f["holder"], {"reservation_date": _future()}
        )
        with pytest.raises(PermissionDeniedError):
            f["service"].reject(f["holder"], item.id)

    def test_approve_flips_status(self, fixtures):
        f = fixtures
        item = f["service"].create(
            f["holder"], {"reservation_date": _future()}
        )
        approved = f["service"].approve(f["admin"], item.id)
        assert approved.status == BBQReservationModel.Status.APPROVED

    def test_reject_flips_status(self, fixtures):
        f = fixtures
        item = f["service"].create(
            f["holder"], {"reservation_date": _future()}
        )
        rejected = f["service"].reject(f["admin"], item.id)
        assert rejected.status == BBQReservationModel.Status.REJECTED

    def test_approve_is_idempotent(self, fixtures):
        f = fixtures
        item = f["book_approved"](f["holder"], reservation_date=_future())
        again = f["service"].approve(f["admin"], item.id)
        assert again.status == BBQReservationModel.Status.APPROVED

    def test_approving_revalidates_against_current_state(self, fixtures):
        """Two PENDING bookings for the same slot exist; admin approves
        the first. Approving the second must now fail because the slot
        is taken."""
        f = fixtures
        d = _future()
        a = f["service"].create(
            f["holder"],
            {
                "reservation_date": d,
                "start_time": time(12, 0),
                "end_time": time(18, 0),
            },
        )
        other = _user(2)
        f["memberships"].add(other.id, _household(2, "1102", "A"))
        b = f["service"].create(
            other,
            {
                "reservation_date": d,
                "start_time": time(15, 0),
                "end_time": time(20, 0),
            },
        )
        f["service"].approve(f["admin"], a.id)
        with pytest.raises(BusinessRuleError):
            f["service"].approve(f["admin"], b.id)

    def test_rejected_booking_does_not_block_others(self, fixtures):
        """A REJECTED booking must free up the slot."""
        f = fixtures
        d = _future()
        a = f["book_approved"](f["holder"], reservation_date=d)
        f["service"].reject(f["admin"], a.id)
        other = _user(2)
        f["memberships"].add(other.id, _household(2, "1102", "A"))
        item = f["book_approved"](other, reservation_date=d)
        assert item is not None

    def test_approve_unknown_id_raises(self, fixtures):
        with pytest.raises(NotFoundError):
            fixtures["service"].approve(fixtures["admin"], 999)


class TestGetAndDelete:
    def test_get_not_found(self, fixtures):
        with pytest.raises(NotFoundError):
            fixtures["service"].get(999)
