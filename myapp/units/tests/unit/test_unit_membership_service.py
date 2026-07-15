"""Unit tests for UnitMembershipService."""

import pytest

from units.models import Unit, UnitMembership, UnitMembershipDecision
from units.services.unit_membership_service import UnitMembershipService
from units.services.unit_service import UnitService
from units.tests.unit._fakes import (
    FakeCondominiumRepository,
    FakeUnitMembershipDecisionRepository,
    FakeUnitMembershipRepository,
    FakeUnitRepository,
    FakeUserRepository,
    make_unit,
    make_user,
)
from shared.exceptions import (
    BusinessRuleError,
    NotFoundError,
    PermissionDeniedError,
)
from shared.infrastructure.transactions import NullTransactionRunner
from shared.test_doubles.fakes import FakeEmailSender


pytestmark = pytest.mark.unit


@pytest.fixture
def fixtures():
    units = FakeUnitRepository()
    memberships = FakeUnitMembershipRepository()
    decisions = FakeUnitMembershipDecisionRepository()
    users = FakeUserRepository()
    email = FakeEmailSender()
    tx = NullTransactionRunner()

    unit_service = UnitService(
        unit_repository=units,
        membership_repository=memberships,
        condominium_repository=FakeCondominiumRepository(),
    )
    membership_service = UnitMembershipService(
        membership_repository=memberships,
        unit_repository=units,
        user_repository=users,
        email_sender=email,
        decision_repository=decisions,
        transaction_runner=tx,
    )

    vacant_unit = units.create(
        {
            "kind": Unit.Kind.APARTMENT,
            "apartment": "101",
            "status": Unit.Status.ACTIVE,
            "condominium_id": 1,
        }
    )
    occupied_unit = units.create(
        {
            "kind": Unit.Kind.APARTMENT,
            "apartment": "202",
            "status": Unit.Status.ACTIVE,
            "condominium_id": 1,
        }
    )
    owner = make_user(1, email="owner@x.com", full_name="Owner")
    memberships.create(
        {
            "unit": occupied_unit,
            "user": owner,
            "role": UnitMembership.Role.OWNER,
            "status": UnitMembership.Status.ACTIVE,
        }
    )

    return {
        "units": units,
        "memberships": memberships,
        "decisions": decisions,
        "users": users,
        "email": email,
        "unit_service": unit_service,
        "service": membership_service,
        "vacant_unit": vacant_unit,
        "occupied_unit": occupied_unit,
        "owner": owner,
        "admin": make_user(99, is_staff=True),
    }


class TestRequestJoin:
    def test_vacant_unit_creates_owner_pending_admin(self, fixtures):
        service = fixtures["service"]
        users = fixtures["users"]
        users.admin_emails = ["admin@example.com"]
        new_user = make_user(2, email="n@x.com")

        membership = service.request_join(new_user, fixtures["vacant_unit"].id)

        assert membership.role == UnitMembership.Role.OWNER
        assert membership.status == UnitMembership.Status.PENDING_ADMIN
        assert any(
            s["kind"] == "household_creation_request" for s in fixtures["email"].sent
        )

    def test_occupied_unit_creates_resident_pending_owner(self, fixtures):
        service = fixtures["service"]
        new_user = make_user(2, email="r@x.com", full_name="Resident")

        membership = service.request_join(new_user, fixtures["occupied_unit"].id)

        assert membership.role == UnitMembership.Role.RESIDENT
        assert membership.status == UnitMembership.Status.PENDING_OWNER
        assert any(
            s["kind"] == "household_join_request" for s in fixtures["email"].sent
        )

    def test_cannot_join_archived_unit(self, fixtures):
        service = fixtures["service"]
        units = fixtures["units"]
        unit = fixtures["vacant_unit"]
        units.update(unit, {"status": Unit.Status.ARCHIVED})
        with pytest.raises(BusinessRuleError):
            service.request_join(make_user(2), unit.id)


class TestApproveReject:
    def test_admin_approves_owner_request(self, fixtures):
        service = fixtures["service"]
        new_user = make_user(2, email="o@x.com", is_active=False)
        membership = service.request_join(new_user, fixtures["vacant_unit"].id)

        result = service.approve(fixtures["admin"], membership.id)

        assert result.status == UnitMembership.Status.ACTIVE
        assert new_user.is_active is True
        decision = fixtures["decisions"].list_for_unit(
            fixtures["vacant_unit"].id
        )[0]
        assert decision.action == UnitMembershipDecision.Action.APPROVED
        assert decision.actor_id == fixtures["admin"].id
        assert decision.target_id == new_user.id

    def test_owner_approves_resident_request(self, fixtures):
        service = fixtures["service"]
        new_user = make_user(2, email="r@x.com", is_active=False)
        membership = service.request_join(new_user, fixtures["occupied_unit"].id)

        result = service.approve(fixtures["owner"], membership.id)

        assert result.status == UnitMembership.Status.ACTIVE
        assert new_user.is_active is True

    def test_non_owner_cannot_approve_resident(self, fixtures):
        service = fixtures["service"]
        new_user = make_user(2)
        membership = service.request_join(new_user, fixtures["occupied_unit"].id)
        with pytest.raises(PermissionDeniedError):
            service.approve(make_user(3), membership.id)

    def test_reject_deletes_pending_membership(self, fixtures):
        service = fixtures["service"]
        users = fixtures["users"]
        new_user = make_user(50, email="r@x.com", is_active=False)
        users._users[new_user.id] = new_user

        membership = service.request_join(new_user, fixtures["occupied_unit"].id)
        service.reject(fixtures["owner"], membership.id, reason="nope")

        assert fixtures["memberships"].get_by_id(membership.id) is None
        assert users.get_by_id(new_user.id) is None
        decision = fixtures["decisions"].list_for_unit(
            fixtures["occupied_unit"].id
        )[0]
        assert decision.action == UnitMembershipDecision.Action.REJECTED
        assert decision.reason == "nope"
        assert decision.target_email == "r@x.com"


class TestProvisionJoin:
    def test_admin_provisions_owner_on_vacant_unit(self, fixtures):
        service = fixtures["service"]
        user = make_user(10)
        membership = service.provision_join(
            fixtures["admin"], user, fixtures["vacant_unit"].id
        )
        assert membership.role == UnitMembership.Role.OWNER
        assert membership.status == UnitMembership.Status.ACTIVE

    def test_admin_provisions_resident_on_occupied_unit(self, fixtures):
        service = fixtures["service"]
        user = make_user(10)
        membership = service.provision_join(
            fixtures["admin"], user, fixtures["occupied_unit"].id
        )
        assert membership.role == UnitMembership.Role.RESIDENT
        assert membership.status == UnitMembership.Status.ACTIVE


class TestLeaveRemove:
    def test_owner_cannot_leave_with_other_members(self, fixtures):
        service = fixtures["service"]
        resident = make_user(2)
        fixtures["memberships"].create(
            {
                "unit": fixtures["occupied_unit"],
                "user": resident,
                "role": UnitMembership.Role.RESIDENT,
                "status": UnitMembership.Status.ACTIVE,
            }
        )
        with pytest.raises(BusinessRuleError):
            service.leave(fixtures["owner"], fixtures["occupied_unit"].id)

    def test_last_member_leave_archives_unit(self, fixtures):
        service = fixtures["service"]
        units = fixtures["units"]
        user = make_user(5)
        unit = fixtures["vacant_unit"]
        fixtures["memberships"].create(
            {
                "unit": unit,
                "user": user,
                "role": UnitMembership.Role.OWNER,
                "status": UnitMembership.Status.ACTIVE,
            }
        )
        service.leave(user, unit.id)
        assert units.get_by_id(unit.id).status == Unit.Status.ARCHIVED

    def test_owner_removes_resident(self, fixtures):
        service = fixtures["service"]
        resident = make_user(2)
        membership = fixtures["memberships"].create(
            {
                "unit": fixtures["occupied_unit"],
                "user": resident,
                "role": UnitMembership.Role.RESIDENT,
                "status": UnitMembership.Status.ACTIVE,
            }
        )
        service.remove(fixtures["owner"], membership.id)
        assert membership.status == UnitMembership.Status.LEFT
