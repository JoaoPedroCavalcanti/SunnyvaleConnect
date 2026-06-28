"""Unit tests for HallReservationService."""

from datetime import date, time, timedelta
from types import SimpleNamespace

import pytest

from hall_reservations.models import HallReservationModel
from hall_reservations.repositories.hall_repository import IHallRepository
from hall_reservations.services.hall_service import HallReservationService
from households.models import HouseholdMembership
from shared.exceptions import (
    BusinessRuleError,
    NotFoundError,
    PermissionDeniedError,
)
from shared.test_doubles.fakes import FakeEmailSender


pytestmark = pytest.mark.unit

TEST_CONDOMINIUM_ID = 1


class FakeHallRepository(IHallRepository):
    def __init__(self):
        self._items = []
        self._next_id = 1

    def list_all(self, status=None, *, condominium_id):
        items = [
            i
            for i in self._items
            if getattr(getattr(i, "household", None), "condominium_id", None)
            == condominium_id
            or getattr(i, "household", None) is None
        ]
        if status:
            return [i for i in items if i.status == status]
        return items

    def get_by_id(self, pk):
        return next((i for i in self._items if i.id == pk), None)

    def list_for_date(self, reservation_date, *, condominium_id):
        return [
            i
            for i in self._items
            if i.reservation_date == reservation_date
            and i.status == HallReservationModel.Status.APPROVED
            and (
                getattr(getattr(i, "household", None), "condominium_id", None)
                == condominium_id
                or getattr(i, "household", None) is None
            )
        ]

    def latest_date_for_household(self, household_id):
        dates = [
            i.reservation_date
            for i in self._items
            if getattr(i, "household", None)
            and i.household.id == household_id
            and i.status == HallReservationModel.Status.APPROVED
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

    def count_by_status(self, status=None, *, condominium_id):
        items = self.list_all(status=status, condominium_id=condominium_id)
        return len(items)


class FakeMembershipRepo:
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
    return SimpleNamespace(
        id=pk, apartment=apt, block=block, condominium_id=TEST_CONDOMINIUM_ID
    )


def _user(pk=1, is_staff=False, email="user@example.com", username="user1"):
    return SimpleNamespace(
        id=pk,
        is_staff=is_staff,
        email=email,
        username=username,
        full_name="",
        condominium_id=TEST_CONDOMINIUM_ID,
    )


def _future(days=10):
    return date.today() + timedelta(days=days)


@pytest.fixture
def fixtures():
    repo = FakeHallRepository()
    memberships = FakeMembershipRepo()
    email = FakeEmailSender()
    service = HallReservationService(
        repository=repo,
        membership_repository=memberships,
        email_sender=email,
    )
    house = _household(1, "1101", "A")
    holder = _user(1)
    admin = _user(99, is_staff=True)
    memberships.add(holder.id, house)

    def book_approved(target_user, **payload):
        return service.create(
            admin, {**payload, "reservation_user": target_user}
        )

    return {
        "service": service,
        "repo": repo,
        "memberships": memberships,
        "email": email,
        "house": house,
        "holder": holder,
        "admin": admin,
        "book_approved": book_approved,
    }


def test_regular_user_creates_for_self(fixtures):
    f = fixtures
    item = f["service"].create(f["holder"], {"reservation_date": _future()})
    assert item.reservation_user is f["holder"]
    assert item.household is f["house"]
    assert item.status == HallReservationModel.Status.PENDING


def test_admin_creation_is_auto_approved(fixtures):
    f = fixtures
    item = f["book_approved"](f["holder"], reservation_date=_future())
    assert item.status == HallReservationModel.Status.APPROVED


def test_pending_does_not_block_other_pending(fixtures):
    f = fixtures
    d = _future()
    f["service"].create(f["holder"], {"reservation_date": d})
    other = _user(2)
    f["memberships"].add(other.id, _household(2, "1102", "A"))
    item = f["service"].create(other, {"reservation_date": d})
    assert item.status == HallReservationModel.Status.PENDING


def test_tolerates_passing_own_id(fixtures):
    f = fixtures
    item = f["service"].create(
        f["holder"],
        {"reservation_date": _future(), "reservation_user": f["holder"]},
    )
    assert item.reservation_user is f["holder"]


def test_regular_user_cannot_pass_another_user(fixtures):
    f = fixtures
    other = _user(2)
    f["memberships"].add(other.id, _household(2, "1102", "A"))
    with pytest.raises(BusinessRuleError):
        f["service"].create(
            f["holder"],
            {"reservation_date": _future(), "reservation_user": other},
        )


def test_user_without_active_household_rejected(fixtures):
    f = fixtures
    homeless = _user(99)
    with pytest.raises(BusinessRuleError):
        f["service"].create(homeless, {"reservation_date": _future()})


def test_admin_must_pass_reservation_user(fixtures):
    f = fixtures
    with pytest.raises(BusinessRuleError):
        f["service"].create(
            _user(is_staff=True), {"reservation_date": _future()}
        )


def test_past_date_rejected(fixtures):
    f = fixtures
    with pytest.raises(BusinessRuleError):
        f["service"].create(
            f["holder"],
            {"reservation_date": date.today() - timedelta(days=1)},
        )


def test_full_day_collides_with_full_day(fixtures):
    f = fixtures
    d = _future()
    f["book_approved"](f["holder"], reservation_date=d)
    other = _user(2)
    f["memberships"].add(other.id, _household(2, "1102", "A"))
    with pytest.raises(BusinessRuleError):
        f["book_approved"](other, reservation_date=d)


def test_full_day_collides_with_any_slot(fixtures):
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


def test_adjacent_slots_are_allowed(fixtures):
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


def test_overlapping_slots_collide(fixtures):
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


def test_open_end_blocks_late_window(fixtures):
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


def test_open_end_allows_earlier_window(fixtures):
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


def test_invalid_slot_start_after_end(fixtures):
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


def test_30_day_window_is_per_household(fixtures):
    f = fixtures
    f["book_approved"](f["holder"], reservation_date=_future(5))
    roommate = _user(2)
    f["memberships"].add(roommate.id, f["house"])
    with pytest.raises(BusinessRuleError):
        f["service"].create(roommate, {"reservation_date": _future(15)})


def test_30_day_window_does_not_cross_households(fixtures):
    f = fixtures
    f["book_approved"](f["holder"], reservation_date=_future(5))
    other = _user(2)
    f["memberships"].add(other.id, _household(2, "1102", "A"))
    item = f["service"].create(other, {"reservation_date": _future(15)})
    assert item is not None


def test_pending_does_not_count_toward_cooldown(fixtures):
    f = fixtures
    f["service"].create(f["holder"], {"reservation_date": _future(5)})
    roommate = _user(2)
    f["memberships"].add(roommate.id, f["house"])
    item = f["service"].create(roommate, {"reservation_date": _future(15)})
    assert item is not None


def test_not_found_on_get(fixtures):
    with pytest.raises(NotFoundError):
        fixtures["service"].get(fixtures["holder"], 999)


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

    def test_reject_requires_reason(self, fixtures):
        f = fixtures
        item = f["service"].create(
            f["holder"], {"reservation_date": _future()}
        )
        with pytest.raises(BusinessRuleError):
            f["service"].reject(f["admin"], item.id)
        with pytest.raises(BusinessRuleError):
            f["service"].reject(f["admin"], item.id, reason="")
        with pytest.raises(BusinessRuleError):
            f["service"].reject(f["admin"], item.id, reason="   ")

    def test_approve_flips_status(self, fixtures):
        f = fixtures
        item = f["service"].create(
            f["holder"], {"reservation_date": _future()}
        )
        approved = f["service"].approve(f["admin"], item.id)
        assert approved.status == HallReservationModel.Status.APPROVED
        assert len(f["email"].sent) == 1
        assert f["email"].sent[0]["kind"] == "reservation_approved"
        assert f["email"].sent[0]["resource_name"] == "party hall"

    def test_approve_skips_email_when_user_has_no_email(self, fixtures):
        f = fixtures
        holder = _user(1, email="")
        f["memberships"].add(holder.id, f["house"])
        item = f["service"].create(
            holder, {"reservation_date": _future()}
        )
        f["service"].approve(f["admin"], item.id)
        assert f["email"].sent == []

    def test_reject_flips_status(self, fixtures):
        f = fixtures
        item = f["service"].create(
            f["holder"], {"reservation_date": _future()}
        )
        rejected = f["service"].reject(f["admin"], item.id, reason="maintenance")
        assert rejected.status == HallReservationModel.Status.REJECTED
        assert len(f["email"].sent) == 1
        assert f["email"].sent[0]["kind"] == "reservation_rejected"
        assert f["email"].sent[0]["resource_name"] == "party hall"
        assert f["email"].sent[0]["reason"] == "maintenance"

    def test_reject_skips_email_when_user_has_no_email(self, fixtures):
        f = fixtures
        holder = _user(1, email="")
        f["memberships"].add(holder.id, f["house"])
        item = f["service"].create(
            holder, {"reservation_date": _future()}
        )
        f["service"].reject(f["admin"], item.id, reason="nope")
        assert f["email"].sent == []

    def test_reject_idempotent_does_not_resend_email(self, fixtures):
        f = fixtures
        item = f["service"].create(
            f["holder"], {"reservation_date": _future()}
        )
        f["service"].reject(f["admin"], item.id, reason="busy")
        f["service"].reject(f["admin"], item.id, reason="busy again")
        assert len(f["email"].sent) == 1

    def test_approving_revalidates_against_current_state(self, fixtures):
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
        f = fixtures
        d = _future()
        a = f["book_approved"](f["holder"], reservation_date=d)
        f["service"].reject(f["admin"], a.id, reason="unavailable")
        other = _user(2)
        f["memberships"].add(other.id, _household(2, "1102", "A"))
        item = f["book_approved"](other, reservation_date=d)
        assert item is not None
