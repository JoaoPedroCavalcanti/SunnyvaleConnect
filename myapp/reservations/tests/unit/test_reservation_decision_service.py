"""Unit tests for ReservationDecisionService."""

from types import SimpleNamespace

import pytest

from reservations.models import ReservationDecision
from reservations.repositories.reservation_decision_repository import (
    IReservationDecisionRepository,
)
from reservations.services.reservation_decision_service import (
    ReservationDecisionService,
)
from shared.exceptions import BusinessRuleError, PermissionDeniedError


pytestmark = pytest.mark.unit


class FakeDecisionRepository(IReservationDecisionRepository):
    def __init__(self, items):
        self.items = items

    def record(self, data):
        raise NotImplementedError

    def list_for_condominium(
        self, condominium_id, *, action=None, location_id=None
    ):
        items = [
            item
            for item in self.items
            if item.condominium_id == condominium_id
        ]
        if action is not None:
            items = [item for item in items if item.action == action]
        if location_id is not None:
            items = [item for item in items if item.location_id == location_id]
        return items


def _user(*, staff=False, condominium_id=1):
    return SimpleNamespace(
        id=1,
        is_staff=staff,
        is_superuser=False,
        is_authenticated=True,
        role="ADMIN" if staff else "RESIDENT",
        condominium_id=condominium_id,
    )


@pytest.fixture
def env():
    decisions = [
        SimpleNamespace(
            id=1,
            condominium_id=1,
            location_id=10,
            action=ReservationDecision.Action.APPROVED,
        ),
        SimpleNamespace(
            id=2,
            condominium_id=1,
            location_id=20,
            action=ReservationDecision.Action.REJECTED,
        ),
        SimpleNamespace(
            id=3,
            condominium_id=2,
            location_id=10,
            action=ReservationDecision.Action.APPROVED,
        ),
    ]
    service = ReservationDecisionService(
        decision_repository=FakeDecisionRepository(decisions)
    )
    return SimpleNamespace(service=service, decisions=decisions)


def test_staff_lists_condo_decision_history(env):
    result = env.service.list_history(_user(staff=True))
    assert [item.id for item in result] == [1, 2]


def test_resident_cannot_list_condo_decision_history(env):
    with pytest.raises(PermissionDeniedError):
        env.service.list_history(_user(staff=False))


def test_history_filters_by_action_and_location(env):
    staff = _user(staff=True)
    approved = env.service.list_history(staff, action="APPROVED")
    assert [item.id for item in approved] == [1]
    by_location = env.service.list_history(staff, location_id=20)
    assert [item.id for item in by_location] == [2]
    with pytest.raises(BusinessRuleError):
        env.service.list_history(staff, action="PENDING")
    with pytest.raises(BusinessRuleError):
        env.service.list_history(staff, location_id="x")
