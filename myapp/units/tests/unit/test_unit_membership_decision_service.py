"""Unit tests for UnitMembershipDecisionService."""

import pytest

from shared.exceptions import (
    BusinessRuleError,
    NotFoundError,
    PermissionDeniedError,
)
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
    return {
        "service": service,
        "unit": unit,
        "owner": owner,
        "decision": decision,
        "memberships": memberships,
        "units": units,
        "decisions": decisions,
    }


def test_active_owner_lists_unit_decisions(env):
    assert env["service"].list_for_unit(env["owner"], env["unit"].id) == [
        env["decision"]
    ]


def test_staff_from_same_condominium_lists_unit_decisions(env):
    assert env["service"].list_for_unit(
        make_user(9, is_staff=True), env["unit"].id
    ) == [env["decision"]]


def test_active_resident_cannot_list_unit_decisions(env):
    resident = make_user(3)
    env["memberships"].create(
        {
            "unit": env["unit"],
            "user": resident,
            "role": UnitMembership.Role.RESIDENT,
            "status": UnitMembership.Status.ACTIVE,
        }
    )

    with pytest.raises(PermissionDeniedError):
        env["service"].list_for_unit(resident, env["unit"].id)


def test_user_from_other_condominium_cannot_see_unit(env):
    with pytest.raises(NotFoundError):
        env["service"].list_for_unit(
            make_user(4, condominium_id=2), env["unit"].id
        )


def test_missing_unit_returns_not_found(env):
    with pytest.raises(NotFoundError):
        env["service"].list_for_unit(env["owner"], 999)


def test_staff_lists_condo_decision_history(env):
    staff = make_user(9, is_staff=True)
    assert env["service"].list_history(staff) == [env["decision"]]


def test_resident_cannot_list_condo_decision_history(env):
    with pytest.raises(PermissionDeniedError):
        env["service"].list_history(env["owner"])


def test_history_scoped_to_caller_condominium(env):
    other_unit = env["units"].create(
        {
            "kind": Unit.Kind.APARTMENT,
            "apartment": "202",
            "status": Unit.Status.ACTIVE,
            "condominium_id": 2,
        }
    )
    other = env["decisions"].record(
        {
            "unit": other_unit,
            "unit_kind": other_unit.kind,
            "unit_name": other_unit.name,
            "unit_apartment": other_unit.apartment,
            "unit_block": other_unit.block,
            "unit_display_name": other_unit.display_name(),
            "actor": make_user(20, is_staff=True, condominium_id=2),
            "actor_username": "admin2",
            "actor_full_name": "Admin 2",
            "target": make_user(21, condominium_id=2),
            "target_username": "other",
            "target_full_name": "Other",
            "target_email": "other@example.com",
            "action": "REJECTED",
            "reason": "nope",
        }
    )
    staff = make_user(9, is_staff=True, condominium_id=1)
    history = env["service"].list_history(staff)
    assert env["decision"] in history
    assert other not in history


def test_history_filters_by_action(env):
    rejected = env["decisions"].record(
        {
            "unit": env["unit"],
            "unit_kind": env["unit"].kind,
            "unit_name": env["unit"].name,
            "unit_apartment": env["unit"].apartment,
            "unit_block": env["unit"].block,
            "unit_display_name": env["unit"].display_name(),
            "actor": env["owner"],
            "actor_username": env["owner"].username,
            "actor_full_name": env["owner"].full_name,
            "target": make_user(30),
            "target_username": "rejected",
            "target_full_name": "Rejected",
            "target_email": "rejected@example.com",
            "action": "REJECTED",
            "reason": "docs",
        }
    )
    staff = make_user(9, is_staff=True)
    approved = env["service"].list_history(staff, action="APPROVED")
    rejected_only = env["service"].list_history(staff, action="REJECTED")
    assert approved == [env["decision"]]
    assert rejected_only == [rejected]


def test_history_rejects_invalid_action(env):
    staff = make_user(9, is_staff=True)
    with pytest.raises(BusinessRuleError) as exc:
        env["service"].list_history(staff, action="PENDING")
    assert exc.value.field == "action"
