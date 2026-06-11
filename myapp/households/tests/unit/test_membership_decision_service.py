"""Unit tests for MembershipDecisionService (the read-only audit listing)."""

import pytest

from households.models import MembershipDecision
from households.services.household_service import HouseholdService
from households.services.membership_decision_service import (
    MembershipDecisionService,
)
from households.services.membership_service import MembershipService
from households.tests.unit._fakes import (
    FakeHouseholdRepository,
    FakeMembershipDecisionRepository,
    FakeMembershipRepository,
    FakeUserRepository,
    make_user,
)
from shared.exceptions import NotFoundError, PermissionDeniedError
from shared.infrastructure.transactions import NullTransactionRunner
from shared.test_doubles.fakes import FakeEmailSender


pytestmark = pytest.mark.unit


@pytest.fixture
def fixtures():
    households = FakeHouseholdRepository()
    memberships = FakeMembershipRepository()
    users = FakeUserRepository()
    decisions = FakeMembershipDecisionRepository()
    email = FakeEmailSender()
    tx = NullTransactionRunner()

    household_service = HouseholdService(
        household_repository=households,
        membership_repository=memberships,
        user_repository=users,
        email_sender=email,
        transaction_runner=tx,
    )
    membership_service = MembershipService(
        membership_repository=memberships,
        household_repository=households,
        user_repository=users,
        email_sender=email,
        decision_repository=decisions,
        transaction_runner=tx,
    )
    decision_service = MembershipDecisionService(
        decision_repository=decisions,
        membership_repository=memberships,
        household_repository=households,
    )

    admin = make_user(99, is_staff=True)
    holder = make_user(1, email="h@x.com", full_name="Holder")
    household = household_service.request_create(holder, "302", "A")
    household_service.approve(admin, household.id)

    # seed an approved request + a rejected request so there's content to list
    approved_user = make_user(2, email="ok@x.com", full_name="Approved One")
    approved_m = membership_service.request_join(approved_user, household.id)
    membership_service.approve(holder, approved_m.id)

    rejected_user = make_user(3, email="no@x.com", full_name="Rejected One")
    rejected_m = membership_service.request_join(rejected_user, household.id)
    membership_service.reject(holder, rejected_m.id, reason="dup")

    return {
        "decision_service": decision_service,
        "household": household,
        "holder": holder,
        "admin": admin,
        "approved_user": approved_user,
    }


class TestListForHousehold:
    def test_holder_lists_decisions(self, fixtures):
        service = fixtures["decision_service"]
        rows = service.list_for_household(
            fixtures["holder"], fixtures["household"].id
        )
        actions = {r.action for r in rows}
        assert actions == {
            MembershipDecision.Action.APPROVED,
            MembershipDecision.Action.REJECTED,
        }

    def test_admin_lists_decisions(self, fixtures):
        service = fixtures["decision_service"]
        rows = service.list_for_household(
            fixtures["admin"], fixtures["household"].id
        )
        assert len(rows) == 2

    def test_resident_blocked(self, fixtures):
        """An active resident (non-holder) cannot read the audit log."""
        service = fixtures["decision_service"]
        with pytest.raises(PermissionDeniedError):
            service.list_for_household(
                fixtures["approved_user"], fixtures["household"].id
            )

    def test_outsider_blocked(self, fixtures):
        service = fixtures["decision_service"]
        with pytest.raises(PermissionDeniedError):
            service.list_for_household(
                make_user(999), fixtures["household"].id
            )

    def test_unknown_household_404(self, fixtures):
        service = fixtures["decision_service"]
        with pytest.raises(NotFoundError):
            service.list_for_household(fixtures["holder"], 9999)
