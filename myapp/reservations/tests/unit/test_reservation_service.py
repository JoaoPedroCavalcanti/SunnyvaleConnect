from datetime import date, datetime, time, timedelta
from types import SimpleNamespace

import pytest

from reservations.models import Reservation
from reservations.repositories.reservation_repository import (
    IReservationRepository,
)
from reservations.services.reservation_service import ReservationService
from shared.exceptions import (
    BusinessRuleError,
    NotFoundError,
    PermissionDeniedError,
)
from shared.test_doubles.fakes import FakeEmailSender


pytestmark = pytest.mark.unit


class FakeReservationRepository(IReservationRepository):
    def __init__(self):
        self.items = []

    def list_for_condominium(
        self,
        condominium_id,
        *,
        status=None,
        period=None,
        reference=None,
    ):
        items = [
            item
            for item in self.items
            if item.condominium_id == condominium_id
            and (not status or item.status == status)
        ]
        if period == "future" and reference:
            today, current_time = reference
            items = [
                item
                for item in items
                if item.reservation_date > today
                or (
                    item.reservation_date == today
                    and (
                        item.end_time is None
                        or item.end_time >= current_time
                    )
                )
            ]
        elif period == "past" and reference:
            today, current_time = reference
            items = [
                item
                for item in items
                if item.reservation_date < today
                or (
                    item.reservation_date == today
                    and item.end_time is not None
                    and item.end_time < current_time
                )
            ]
        return items

    def list_for_user(
        self,
        user_id,
        condominium_id,
        *,
        status=None,
        period=None,
        reference=None,
    ):
        return [
            item
            for item in self.list_for_condominium(
                condominium_id,
                status=status,
                period=period,
                reference=reference,
            )
            if item.reservation_user_id == user_id
        ]

    def get_by_id(self, pk):
        return next((item for item in self.items if item.id == pk), None)

    def list_blocking_for_location_date(
        self, location_id, reservation_date, *, exclude_id=None
    ):
        return [
            item
            for item in self.items
            if item.location_id == location_id
            and item.reservation_date == reservation_date
            and item.status
            in {Reservation.Status.PENDING, Reservation.Status.APPROVED}
            and item.id != exclude_id
        ]

    def list_blocking_between(self, location_id, from_date, to_date):
        return [
            item
            for item in self.items
            if item.location_id == location_id
            and from_date <= item.reservation_date <= to_date
            and item.status
            in {Reservation.Status.PENDING, Reservation.Status.APPROVED}
        ]

    def count_by_status(self, status, *, condominium_id):
        return len(
            [
                item
                for item in self.items
                if item.condominium_id == condominium_id
                and item.status == status
            ]
        )

    def create(self, data):
        item = SimpleNamespace(
            id=len(self.items) + 1,
            condominium_id=data["condominium"].id,
            location_id=data["location"].id,
            reservation_user_id=(
                data["reservation_user"].id
                if data["reservation_user"]
                else None
            ),
            unit_id=data["unit"].id if data["unit"] else None,
            start_time=data.get("start_time"),
            end_time=data.get("end_time"),
            guest_count=data.get("guest_count"),
            **{
                key: value
                for key, value in data.items()
                if key
                not in {
                    "start_time",
                    "end_time",
                    "guest_count",
                }
            },
        )
        self.items.append(item)
        return item

    def update(self, instance, data):
        for key, value in data.items():
            setattr(instance, key, value)
        if "location" in data:
            instance.location_id = data["location"].id
            instance.condominium_id = data["condominium"].id
        if "reservation_user" in data:
            instance.reservation_user_id = (
                data["reservation_user"].id
                if data["reservation_user"]
                else None
            )
        return instance

    def delete(self, instance):
        self.items.remove(instance)


class FakeLocationRepository:
    def __init__(self, locations):
        self.locations = locations

    def get_by_id(self, pk):
        return next(
            (location for location in self.locations if location.id == pk),
            None,
        )


class FakeMembershipRepository:
    def __init__(self, memberships):
        self.memberships = memberships

    def list_active_for_user(self, user_id):
        return [
            membership
            for membership in self.memberships
            if membership.user_id == user_id
        ]


class FakeUserRepository:
    def __init__(self, users):
        self.users = users

    def get_by_id(self, pk):
        return next((user for user in self.users if user.id == pk), None)


def _user(pk, *, staff=False, condominium_id=1):
    return SimpleNamespace(
        id=pk,
        is_staff=staff,
        is_superuser=False,
        is_authenticated=True,
        role="ADMIN" if staff else "RESIDENT",
        condominium_id=condominium_id,
        email=f"user{pk}@example.com",
        username=f"user{pk}",
        full_name=f"User {pk}",
    )


@pytest.fixture
def setup():
    condominium = SimpleNamespace(id=1)
    location = SimpleNamespace(
        id=1,
        name="Party Hall",
        condominium=condominium,
        condominium_id=1,
        is_active=True,
    )
    other_location = SimpleNamespace(
        id=2,
        name="Barbecue",
        condominium=condominium,
        condominium_id=1,
        is_active=True,
    )
    resident = _user(1)
    other = _user(2)
    staff = _user(3, staff=True)
    unit = SimpleNamespace(
        id=1,
        condominium_id=1,
        display_name=lambda: "Apt 101",
    )
    memberships = [
        SimpleNamespace(user_id=resident.id, unit=unit),
        SimpleNamespace(user_id=other.id, unit=unit),
    ]
    repository = FakeReservationRepository()
    email = FakeEmailSender()
    service = ReservationService(
        repository=repository,
        location_repository=FakeLocationRepository(
            [location, other_location]
        ),
        membership_repository=FakeMembershipRepository(memberships),
        user_repository=FakeUserRepository([resident, other, staff]),
        email_sender=email,
    )
    return SimpleNamespace(
        service=service,
        repository=repository,
        location=location,
        other_location=other_location,
        resident=resident,
        other=other,
        staff=staff,
        email=email,
    )


def _future(days=10):
    return date.today() + timedelta(days=days)


def _payload(location_id=1, **overrides):
    return {
        "location_id": location_id,
        "reservation_date": _future(),
        **overrides,
    }


def test_resident_pending_and_staff_approved(setup):
    pending = setup.service.create(
        setup.resident, _payload()
    )
    approved = setup.service.create(
        setup.staff,
        _payload(
            location_id=2,
            reservation_user_id=setup.other.id,
        ),
    )
    assert pending.status == Reservation.Status.PENDING
    assert approved.status == Reservation.Status.APPROVED


def test_pending_blocks_same_slot_but_other_location_is_allowed(setup):
    first = setup.service.create(
        setup.resident,
        _payload(start_time=time(10), end_time=time(12)),
    )
    with pytest.raises(BusinessRuleError):
        setup.service.create(
            setup.other,
            _payload(start_time=time(10), end_time=time(12)),
        )
    setup.service.create(
        setup.staff,
        _payload(
            location_id=2,
            start_time=time(10),
            end_time=time(12),
        ),
    )
    setup.service.approve(setup.staff, first.id)
    with pytest.raises(BusinessRuleError):
        setup.service.create(
            setup.staff,
            _payload(start_time=time(11), end_time=time(13)),
        )


def test_approval_excludes_the_pending_reservation_itself(setup):
    first = setup.service.create(setup.resident, _payload())
    approved = setup.service.approve(setup.staff, first.id)
    assert approved.status == Reservation.Status.APPROVED


def test_approved_patch_excludes_itself_and_revalidates(setup):
    item = setup.service.create(
        setup.staff,
        _payload(start_time=time(10), end_time=time(12)),
    )
    updated = setup.service.update(
        setup.staff, item.id, {"end_time": time(12, 30)}
    )
    assert updated.end_time == time(12, 30)


def test_edit_permissions_follow_reservation_status(setup):
    pending = setup.service.create(
        setup.resident,
        _payload(start_time=time(10), end_time=time(12)),
    )
    updated_pending = setup.service.update(
        setup.resident,
        pending.id,
        {
            "start_time": time(11),
            "end_time": time(13),
            "guest_count": 8,
        },
    )
    assert updated_pending.start_time == time(11)
    assert updated_pending.guest_count == 8

    approved = setup.service.approve(setup.staff, pending.id)
    with pytest.raises(PermissionDeniedError):
        setup.service.update(
            setup.resident,
            approved.id,
            {"guest_count": 10},
        )

    updated_approved = setup.service.update(
        setup.staff,
        approved.id,
        {
            "start_time": time(12),
            "end_time": time(14),
            "guest_count": 12,
        },
    )
    assert updated_approved.start_time == time(12)
    assert updated_approved.guest_count == 12
    with pytest.raises(BusinessRuleError) as exc_info:
        setup.service.update(
            setup.staff,
            approved.id,
            {"location_id": setup.other_location.id},
        )
    assert exc_info.value.field == "location_id"

    rejected = setup.service.create(
        setup.other,
        _payload(location_id=2),
    )
    setup.service.reject(setup.staff, rejected.id, reason="maintenance")
    with pytest.raises(BusinessRuleError):
        setup.service.update(
            setup.staff,
            rejected.id,
            {"guest_count": 5},
        )


def test_pending_and_approved_future_reservations_can_be_deleted(setup):
    pending = setup.service.create(setup.resident, _payload())
    setup.service.delete(setup.resident, pending.id)
    assert setup.repository.get_by_id(pending.id) is None

    approved = setup.service.create(
        setup.staff,
        _payload(reservation_user_id=setup.resident.id),
    )
    setup.service.delete(setup.staff, approved.id)
    assert setup.repository.get_by_id(approved.id) is None


def test_rejected_reservation_cannot_be_deleted(setup):
    item = setup.service.create(setup.resident, _payload())
    setup.service.reject(setup.staff, item.id, reason="maintenance")

    with pytest.raises(BusinessRuleError) as exc:
        setup.service.delete(setup.resident, item.id)

    assert exc.value.field == "status"
    assert setup.repository.get_by_id(item.id) is item


def test_past_reservation_cannot_be_deleted(setup):
    item = setup.service.create(setup.resident, _payload())
    item.reservation_date = date.today() - timedelta(days=1)

    with pytest.raises(BusinessRuleError) as exc:
        setup.service.delete(setup.resident, item.id)

    assert exc.value.field == "reservation_date"
    assert setup.repository.get_by_id(item.id) is item


def test_regular_user_ownership_is_hidden_as_not_found(setup):
    item = setup.service.create(setup.other, _payload())
    with pytest.raises(NotFoundError):
        setup.service.get(setup.resident, item.id)


def test_regular_user_cannot_target_another_user(setup):
    with pytest.raises(PermissionDeniedError):
        setup.service.create(
            setup.resident,
            _payload(reservation_user_id=setup.other.id),
        )


def test_inactive_location_and_past_date_are_rejected(setup):
    setup.location.is_active = False
    with pytest.raises(NotFoundError):
        setup.service.create(setup.resident, _payload())
    setup.location.is_active = True
    with pytest.raises(BusinessRuleError):
        setup.service.create(
            setup.resident,
            _payload(
                reservation_date=date.today() - timedelta(days=1)
            ),
        )


def test_today_reservation_cannot_start_before_current_time(
    setup, monkeypatch
):
    from reservations.services import reservation_service

    monkeypatch.setattr(
        reservation_service.timezone,
        "localdate",
        lambda: date(2026, 7, 15),
    )
    monkeypatch.setattr(
        reservation_service.timezone,
        "localtime",
        lambda: datetime(2026, 7, 15, 15, 43),
    )

    with pytest.raises(BusinessRuleError) as exc_info:
        setup.service.create(
            setup.resident,
            _payload(
                reservation_date=date(2026, 7, 15),
                start_time=time(10),
                end_time=time(11),
            ),
        )

    assert exc_info.value.field == "start_time"
    created = setup.service.create(
        setup.resident,
        _payload(
            location_id=2,
            reservation_date=date(2026, 7, 15),
            start_time=time(16),
            end_time=time(17),
        ),
    )
    assert created.start_time == time(16)


def test_list_can_filter_reservations_by_period(setup, monkeypatch):
    from reservations.services import reservation_service

    monkeypatch.setattr(
        reservation_service.timezone,
        "localdate",
        lambda: date(2026, 7, 15),
    )
    monkeypatch.setattr(
        reservation_service.timezone,
        "localtime",
        lambda: datetime(2026, 7, 15, 15, 43),
    )
    upcoming = setup.service.create(
        setup.resident,
        _payload(
            reservation_date=date(2026, 7, 15),
            start_time=time(16),
            end_time=time(17),
        ),
    )
    tomorrow = setup.service.create(
        setup.resident,
        _payload(
            location_id=2,
            reservation_date=date(2026, 7, 16),
        ),
    )
    past = SimpleNamespace(**vars(upcoming))
    past.id = 999
    past.reservation_date = date(2026, 7, 14)
    setup.repository.items.append(past)
    expired_today = SimpleNamespace(**vars(upcoming))
    expired_today.id = 998
    expired_today.start_time = time(7)
    expired_today.end_time = time(8)
    setup.repository.items.append(expired_today)
    ongoing = SimpleNamespace(**vars(upcoming))
    ongoing.id = 997
    ongoing.start_time = time(15)
    ongoing.end_time = time(16)
    setup.repository.items.append(ongoing)

    future_result = setup.service.list(
        setup.resident, period="future"
    )
    past_result = setup.service.list(setup.resident, period="past")

    assert {item.id for item in future_result} == {
        upcoming.id,
        tomorrow.id,
        ongoing.id,
    }
    assert {item.id for item in past_result} == {
        past.id,
        expired_today.id,
    }
    assert {
        item.id for item in future_result
    }.isdisjoint(item.id for item in past_result)
    with pytest.raises(BusinessRuleError):
        setup.service.list(setup.resident, period="invalid")


def test_reject_requires_reason_and_email_uses_location_name(setup):
    item = setup.service.create(setup.resident, _payload())
    with pytest.raises(BusinessRuleError):
        setup.service.reject(setup.staff, item.id, reason=" ")
    setup.service.reject(setup.staff, item.id, reason="maintenance")
    assert setup.email.sent[0]["resource_name"] == "Party Hall"


def test_availability_is_location_specific_and_limited(setup):
    with pytest.raises(BusinessRuleError):
        setup.service.availability(
            setup.resident,
            setup.location.id,
            from_date=_future(),
            to_date=_future(103),
        )


def test_pending_reservation_marks_calendar_partial_for_other_users(setup):
    pending = setup.service.create(
        setup.resident,
        _payload(start_time=time(10), end_time=time(12)),
    )

    result = setup.service.availability(
        setup.other,
        setup.location.id,
        from_date=pending.reservation_date,
        to_date=pending.reservation_date,
    )

    day = result.days[0]
    assert day.status == "partial"
    assert [booking.status for booking in day.bookings] == [
        Reservation.Status.PENDING
    ]
    assert day.bookings[0].id == pending.id
    assert all(
        not (
            slot.start_time < time(12, 30)
            and slot.end_time > time(9, 30)
        )
        for slot in day.free_slots
    )
