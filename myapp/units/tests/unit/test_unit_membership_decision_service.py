"""Unit tests for UnitMembershipDecisionService."""

import pytest

from shared.exceptions import NotFoundError, PermissionDeniedError
from units.models import Unit, UnitMembership
from units.services.unit_membership_decision_service import (
    UnitMembershipDecisionService,
)
from units.tests.unit._fakes import (
    FakeUnitMembershipDecisionRepository,
    FakeUnitMembershipRepository,
    FakeUnitRepository,
    make_user,
)


pytestmark = pytest.mark.unit


@pytest.fixture
def env():
    units = FakeUnitRepository()
    memberships = FakeUnitMembershipRepository()
    decisions = FakeUnitMembershipDecisionRepository()
    unit = units.create(
        {
            "kind": Unit.Kind.APARTMENT,
            "apartment": "101",
            "status": Unit.Status.ACTIVE,
            "condominium_id": 1,
        }
    )
    owner = make_user(1)
    memberships.create(
        {
            "unit": unit,
            "user": owner,
            "role": UnitMembership.Role.OWNER,
            "status": UnitMembership.Status.ACTIVE,
        }
    )
    decision = decisions.record(
        {
            "unit": unit,
            "unit_kind": unit.kind,
            "unit_name": unit.name,
            "unit_apartment": unit.apartment,
            "unit_block": unit.block,
            "unit_display_name": unit.display_name(),
            "actor": owner,
            "actor_username": owner.username,
            "actor_full_name": owner.full_name,
            "target": make_user(2),
            "target_username": "resident",
            "target_full_name": "Resident",
            "target_email": "resident@example.com",
            "action": "APPROVED",
            "reason": "",
        }
    )
    service = UnitMembershipDecisionService(
        decision_repository=decisions,
        membership_repository=memberships,
        unit_repository=units,
    )
    return service, unit, owner, decision, memberships


def test_active_owner_lists_unit_decisions(env):
    service, unit, owner, decision, _ = env

    assert service.list_for_unit(owner, unit.id) == [decision]


def test_staff_from_same_condominium_lists_unit_decisions(env):
    service, unit, _, decision, _ = env

    assert service.list_for_unit(make_user(9, is_staff=True), unit.id) == [
        decision
    ]


def test_active_resident_cannot_list_unit_decisions(env):
    service, unit, _, _, memberships = env
    resident = make_user(3)
    memberships.create(
        {
            "unit": unit,
            "user": resident,
            "role": UnitMembership.Role.RESIDENT,
            "status": UnitMembership.Status.ACTIVE,
        }
    )

    with pytest.raises(PermissionDeniedError):
        service.list_for_unit(resident, unit.id)


def test_user_from_other_condominium_cannot_see_unit(env):
    service, unit, _, _, _ = env

    with pytest.raises(NotFoundError):
        service.list_for_unit(make_user(4, condominium_id=2), unit.id)


def test_missing_unit_returns_not_found(env):
    service, _, owner, _, _ = env

    with pytest.raises(NotFoundError):
        service.list_for_unit(owner, 999)
