"""Unit tests for MembershipService."""

import pytest

from households.models import Household, HouseholdMembership, MembershipDecision
from households.services.household_service import HouseholdService
from households.services.membership_service import MembershipService
from households.tests.unit._fakes import (
    FakeHouseholdRepository,
    FakeMembershipDecisionRepository,
    FakeMembershipRepository,
    FakeUserRepository,
    make_user,
)
from shared.exceptions import (
    BusinessRuleError,
    NotFoundError,
    PermissionDeniedError,
)
from shared.test_doubles.fakes import FakeEmailSender


pytestmark = pytest.mark.unit


@pytest.fixture
def fixtures():
    households = FakeHouseholdRepository()
    memberships = FakeMembershipRepository()
    users = FakeUserRepository()
    decisions = FakeMembershipDecisionRepository()
    email = FakeEmailSender()

    household_service = HouseholdService(
        household_repository=households,
        membership_repository=memberships,
        user_repository=users,
        email_sender=email,
    )
    membership_service = MembershipService(
        membership_repository=memberships,
        household_repository=households,
        user_repository=users,
        email_sender=email,
        decision_repository=decisions,
    )

    holder = make_user(1, email="h@x.com", full_name="Holder")
    household = household_service.request_create(holder, "302", "A")
    admin = make_user(99, is_staff=True)
    household_service.approve(admin, household.id)

    return {
        "households": households,
        "memberships": memberships,
        "users": users,
        "decisions": decisions,
        "email": email,
        "household_service": household_service,
        "service": membership_service,
        "holder": holder,
        "household": household,
        "admin": admin,
    }


class TestRequestJoin:
    def test_resident_pending_membership_and_notifies_holder(self, fixtures):
        service = fixtures["service"]
        household = fixtures["household"]
        email = fixtures["email"]

        new_user = make_user(2, email="r@x.com", full_name="Resident")
        membership = service.request_join(new_user, household.id)

        assert membership.role == HouseholdMembership.Role.RESIDENT
        assert membership.status == HouseholdMembership.Status.PENDING_HOLDER
        assert any(s["kind"] == "household_join_request" for s in email.sent)

    def test_cannot_request_inactive_household(self, fixtures):
        service = fixtures["service"]
        households = fixtures["households"]
        household = fixtures["household"]
        households.update(household, {"status": Household.Status.ARCHIVED})
        with pytest.raises(BusinessRuleError):
            service.request_join(make_user(2), household.id)

    def test_double_request_rejected(self, fixtures):
        service = fixtures["service"]
        new_user = make_user(2)
        service.request_join(new_user, fixtures["household"].id)
        with pytest.raises(BusinessRuleError):
            service.request_join(new_user, fixtures["household"].id)


class TestApproveReject:
    def test_holder_approves(self, fixtures):
        service = fixtures["service"]
        new_user = make_user(2, email="r@x.com", is_active=False)
        membership = service.request_join(new_user, fixtures["household"].id)
        result = service.approve(fixtures["holder"], membership.id)
        assert result.status == HouseholdMembership.Status.ACTIVE
        assert new_user.is_active is True

    def test_approve_records_audit_entry(self, fixtures):
        service = fixtures["service"]
        new_user = make_user(2, email="r@x.com", full_name="New", is_active=False)
        membership = service.request_join(new_user, fixtures["household"].id)
        service.approve(fixtures["holder"], membership.id)

        rows = fixtures["decisions"].list_for_household(
            fixtures["household"].id
        )
        assert len(rows) == 1
        entry = rows[0]
        assert entry.action == MembershipDecision.Action.APPROVED
        assert entry.actor_id == fixtures["holder"].id
        assert entry.target_id == new_user.id
        assert entry.target_full_name == "New"
        assert entry.reason == ""

    def test_non_holder_cannot_approve(self, fixtures):
        service = fixtures["service"]
        new_user = make_user(2)
        membership = service.request_join(new_user, fixtures["household"].id)
        with pytest.raises(PermissionDeniedError):
            service.approve(make_user(3), membership.id)

    def test_reject_deletes_membership_and_pending_only_user(self, fixtures):
        service = fixtures["service"]
        users = fixtures["users"]
        new_user = make_user(50, email="r@x.com", is_active=False)
        users._users[new_user.id] = new_user

        membership = service.request_join(new_user, fixtures["household"].id)
        service.reject(fixtures["holder"], membership.id, reason="nope")

        assert fixtures["memberships"].get_by_id(membership.id) is None
        assert users.get_by_id(new_user.id) is None

    def test_reject_records_audit_entry_with_snapshot(self, fixtures):
        """Reject deletes the user; the snapshot must survive."""
        service = fixtures["service"]
        users = fixtures["users"]
        new_user = make_user(
            50, email="r@x.com", full_name="Rejected One", is_active=False
        )
        users._users[new_user.id] = new_user

        membership = service.request_join(new_user, fixtures["household"].id)
        service.reject(fixtures["holder"], membership.id, reason="not approved")

        rows = fixtures["decisions"].list_for_household(
            fixtures["household"].id
        )
        assert len(rows) == 1
        entry = rows[0]
        assert entry.action == MembershipDecision.Action.REJECTED
        assert entry.target_full_name == "Rejected One"
        assert entry.target_email == "r@x.com"
        assert entry.reason == "not approved"


class TestPromoteDemote:
    def _seed_resident(self, fixtures):
        service = fixtures["service"]
        u = make_user(2, email="r@x.com")
        m = service.request_join(u, fixtures["household"].id)
        service.approve(fixtures["holder"], m.id)
        return u, m

    def test_promote_resident_to_holder(self, fixtures):
        service = fixtures["service"]
        _, membership = self._seed_resident(fixtures)
        result = service.promote(fixtures["holder"], membership.id)
        assert result.role == HouseholdMembership.Role.HOLDER

    def test_cannot_demote_last_holder(self, fixtures):
        service = fixtures["service"]
        # only one holder exists; trying to demote should fail
        m = fixtures["memberships"].get_for_user_and_household(
            fixtures["holder"].id, fixtures["household"].id
        )
        with pytest.raises(BusinessRuleError):
            service.demote(fixtures["holder"], m.id)

    def test_demote_after_promote_ok(self, fixtures):
        service = fixtures["service"]
        _, membership = self._seed_resident(fixtures)
        service.promote(fixtures["holder"], membership.id)
        result = service.demote(fixtures["holder"], membership.id)
        assert result.role == HouseholdMembership.Role.RESIDENT


class TestRemoveLeave:
    def test_holder_removes_resident(self, fixtures):
        service = fixtures["service"]
        u = make_user(2, email="r@x.com")
        m = service.request_join(u, fixtures["household"].id)
        service.approve(fixtures["holder"], m.id)
        service.remove(fixtures["holder"], m.id)
        assert m.status == HouseholdMembership.Status.LEFT

    def test_holder_cannot_remove_self_via_remove(self, fixtures):
        service = fixtures["service"]
        m = fixtures["memberships"].get_for_user_and_household(
            fixtures["holder"].id, fixtures["household"].id
        )
        with pytest.raises(BusinessRuleError):
            service.remove(fixtures["holder"], m.id)

    def test_holder_cannot_remove_another_holder_directly(self, fixtures):
        service = fixtures["service"]
        u = make_user(2)
        m = service.request_join(u, fixtures["household"].id)
        service.approve(fixtures["holder"], m.id)
        service.promote(fixtures["holder"], m.id)
        with pytest.raises(BusinessRuleError):
            service.remove(fixtures["holder"], m.id)

    def test_last_holder_with_residents_cannot_leave(self, fixtures):
        service = fixtures["service"]
        # add a resident so the holder is the last *holder* but not the last *member*
        u = make_user(2, email="r@x.com")
        m = service.request_join(u, fixtures["household"].id)
        service.approve(fixtures["holder"], m.id)

        with pytest.raises(BusinessRuleError):
            service.leave(fixtures["holder"], fixtures["household"].id)

    def test_sole_member_holder_can_leave_and_household_archives(self, fixtures):
        service = fixtures["service"]
        service.leave(fixtures["holder"], fixtures["household"].id)
        assert fixtures["household"].status == Household.Status.ARCHIVED

    def test_leave_archives_household_when_empty(self, fixtures):
        service = fixtures["service"]
        u = make_user(2, email="r@x.com")
        m = service.request_join(u, fixtures["household"].id)
        service.approve(fixtures["holder"], m.id)
        service.promote(fixtures["holder"], m.id)
        service.leave(fixtures["holder"], fixtures["household"].id)
        service.leave(u, fixtures["household"].id)
        assert fixtures["household"].status == Household.Status.ARCHIVED


class TestTransfer:
    def test_transfer_promotes_target(self, fixtures):
        service = fixtures["service"]
        u = make_user(2)
        m = service.request_join(u, fixtures["household"].id)
        service.approve(fixtures["holder"], m.id)
        result = service.transfer(
            fixtures["holder"], fixtures["household"].id, u.id
        )
        assert result.role == HouseholdMembership.Role.HOLDER

    def test_cannot_transfer_to_non_member(self, fixtures):
        service = fixtures["service"]
        with pytest.raises(BusinessRuleError):
            service.transfer(
                fixtures["holder"], fixtures["household"].id, 999
            )


class TestListForHousehold:
    def test_member_can_list(self, fixtures):
        service = fixtures["service"]
        result = service.list_for_household(
            fixtures["holder"], fixtures["household"].id
        )
        assert len(result) == 1

    def test_non_member_blocked(self, fixtures):
        service = fixtures["service"]
        with pytest.raises(PermissionDeniedError):
            service.list_for_household(make_user(99), fixtures["household"].id)

    def test_unknown_household_404(self, fixtures):
        service = fixtures["service"]
        with pytest.raises(NotFoundError):
            service.list_for_household(fixtures["holder"], 9999)


class TestListPendingApprovals:
    def test_holder_sees_pending_residents_of_own_household(self, fixtures):
        service = fixtures["service"]
        u = make_user(2, email="r@x.com")
        service.request_join(u, fixtures["household"].id)

        result = service.list_pending_approvals(fixtures["holder"])
        assert len(result) == 1
        assert result[0].user_id == u.id

    def test_holder_does_not_see_pending_of_other_households(self, fixtures):
        service = fixtures["service"]
        household_service = fixtures["household_service"]
        # second household with a different holder
        other_holder = make_user(50, email="other@x.com")
        other_household = household_service.request_create(
            other_holder, "999", "Z"
        )
        household_service.approve(
            make_user(99, is_staff=True), other_household.id
        )
        # someone asks to join the other household
        intruder = make_user(60, email="i@x.com")
        service.request_join(intruder, other_household.id)

        result = service.list_pending_approvals(fixtures["holder"])
        assert all(m.household_id == fixtures["household"].id for m in result)

    def test_admin_sees_all_pending_admin_memberships(self, fixtures):
        service = fixtures["service"]
        household_service = fixtures["household_service"]
        pending_user = make_user(70, email="p@x.com", is_active=False)
        household_service.request_create(pending_user, "555", "Y")

        result = service.list_pending_approvals(make_user(99, is_staff=True))
        assert any(
            m.status == HouseholdMembership.Status.PENDING_ADMIN for m in result
        )

    def test_regular_user_with_no_holder_role_gets_empty(self, fixtures):
        service = fixtures["service"]
        assert service.list_pending_approvals(make_user(123)) == []
