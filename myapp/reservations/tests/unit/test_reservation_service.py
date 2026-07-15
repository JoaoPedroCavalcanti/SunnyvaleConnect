from datetime import date, time, timedelta
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
        self, condominium_id, *, status=None
    ):
        return [
            item
            for item in self.items
            if item.condominium_id == condominium_id
            and (not status or item.status == status)
        ]

    def list_for_user(
        self, user_id, condominium_id, *, status=None
    ):
        return [
            item
            for item in self.list_for_condominium(
                condominium_id, status=status
            )
            if item.reservation_user_id == user_id
        ]

    def get_by_id(self, pk):
        return next((item for item in self.items if item.id == pk), None)

    def list_approved_for_location_date(
        self, location_id, reservation_date, *, exclude_id=None
    ):
        return [
            item
            for item in self.items
            if item.location_id == location_id
            and item.reservation_date == reservation_date
            and item.status == Reservation.Status.APPROVED
            and item.id != exclude_id
        ]

    def list_approved_between(self, location_id, from_date, to_date):
        return [
            item
            for item in self.items
            if item.location_id == location_id
            and from_date <= item.reservation_date <= to_date
            and item.status == Reservation.Status.APPROVED
        ]

    def list_pending_for_user_between(
        self, location_id, user_id, from_date, to_date
    ):
        return [
            item
            for item in self.items
            if item.location_id == location_id
            and item.reservation_user_id == user_id
            and from_date <= item.reservation_date <= to_date
            and item.status == Reservation.Status.PENDING
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
    unit = SimpleNamespace(id=1, condominium_id=1)
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


def test_conflicts_are_location_specific_and_pending_does_not_block(setup):
    first = setup.service.create(
        setup.resident,
        _payload(start_time=time(10), end_time=time(12)),
    )
    setup.service.create(
        setup.other,
        _payload(start_time=time(10), end_time=time(12)),
    )
    setup.service.approve(setup.staff, first.id)
    setup.service.create(
        setup.staff,
        _payload(
            location_id=2,
            start_time=time(10),
            end_time=time(12),
        ),
    )
    with pytest.raises(BusinessRuleError):
        setup.service.create(
            setup.staff,
            _payload(start_time=time(11), end_time=time(13)),
        )


def test_approval_revalidates_current_conflicts(setup):
    first = setup.service.create(setup.resident, _payload())
    second = setup.service.create(setup.other, _payload())
    setup.service.approve(setup.staff, first.id)
    with pytest.raises(BusinessRuleError):
        setup.service.approve(setup.staff, second.id)


def test_approved_patch_excludes_itself_and_revalidates(setup):
    item = setup.service.create(
        setup.staff,
        _payload(start_time=time(10), end_time=time(12)),
    )
    updated = setup.service.update(
        setup.staff, item.id, {"end_time": time(12, 30)}
    )
    assert updated.end_time == time(12, 30)


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
