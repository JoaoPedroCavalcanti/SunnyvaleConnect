"""Unit tests for HouseholdService."""

import pytest

from households.models import Household, HouseholdMembership
from households.services.household_service import HouseholdService
from households.tests.unit._fakes import (
    FakeCondominiumRepository,
    FakeHouseholdRepository,
    FakeMembershipRepository,
    FakeUserRepository,
    TEST_CONDOMINIUM_CODE,
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
def deps():
    households = FakeHouseholdRepository()
    memberships = FakeMembershipRepository()
    users = FakeUserRepository()
    email = FakeEmailSender()
    service = HouseholdService(
        household_repository=households,
        membership_repository=memberships,
        user_repository=users,
        email_sender=email,
        transaction_runner=NullTransactionRunner(),
        condominium_repository=FakeCondominiumRepository(),
    )
    return service, households, memberships, users, email


class TestRequestCreate:
    def test_creates_pending_household_and_holder_membership(self, deps):
        service, households, memberships, users, email = deps
        users.admin_emails = ["admin@example.com"]
        user = make_user(1, full_name="João")

        household = service.request_create(user, "302", "A")

        assert household.status == Household.Status.PENDING_ADMIN
        ms = memberships.list_for_household(household.id)
        assert len(ms) == 1
        assert ms[0].role == HouseholdMembership.Role.HOLDER
        assert ms[0].status == HouseholdMembership.Status.PENDING_ADMIN
        assert any(s["kind"] == "household_creation_request" for s in email.sent)

    def test_duplicate_apartment_block_rejected(self, deps):
        service, *_ = deps
        user = make_user(1)
        service.request_create(user, "302", "A")
        with pytest.raises(BusinessRuleError) as exc:
            service.request_create(make_user(2), "302", "A")
        assert exc.value.field == "apartment"

    def test_empty_apartment_rejected(self, deps):
        service, *_ = deps
        with pytest.raises(BusinessRuleError):
            service.request_create(make_user(1), "", "A")


class TestApprove:
    def test_admin_approves_household_and_activates_holder(self, deps):
        service, _, memberships, users, email = deps
        user = make_user(1, email="j@x.com", is_active=False, full_name="J")
        household = service.request_create(user, "302", "A")
        admin = make_user(99, is_staff=True)

        service.approve(admin, household.id)

        assert household.status == Household.Status.ACTIVE
        m = memberships.list_for_household(household.id)[0]
        assert m.status == HouseholdMembership.Status.ACTIVE
        assert user.is_active is True
        assert any(s["kind"] == "household_approved" for s in email.sent)

    def test_non_admin_cannot_approve(self, deps):
        service, *_ = deps
        user = make_user(1)
        household = service.request_create(user, "302", "A")
        with pytest.raises(PermissionDeniedError):
            service.approve(make_user(2), household.id)

    def test_approve_already_active_rejected(self, deps):
        service, *_ = deps
        user = make_user(1, is_active=False)
        household = service.request_create(user, "302", "A")
        admin = make_user(99, is_staff=True)
        service.approve(admin, household.id)
        with pytest.raises(BusinessRuleError):
            service.approve(admin, household.id)


class TestReject:
    def test_admin_rejects_deletes_household_and_user(self, deps):
        service, households, memberships, users, email = deps
        user_obj = users.create_user(
            username="j",
            password="x",
            email="j@x.com",
            full_name="J",
            cpf="",
            phone="",
            apartment="302",
            block="A",
            birth_date=None,
            is_active=False,
        )
        household = service.request_create(user_obj, "302", "A")
        admin = make_user(99, is_staff=True)

        service.reject(admin, household.id, reason="not ok")

        assert households.get_by_id(household.id) is None
        assert users.get_by_id(user_obj.id) is None
        assert any(s["kind"] == "household_rejected" for s in email.sent)


class TestListAndGet:
    def test_admin_lists_all(self, deps):
        service, *_ = deps
        service.request_create(make_user(1), "101", "A")
        service.request_create(make_user(2), "102", "A")
        admin = make_user(99, is_staff=True)
        assert len(service.list_for(admin)) == 2

    def test_get_for_404_when_not_member(self, deps):
        service, *_ = deps
        h = service.request_create(make_user(1), "101", "A")
        with pytest.raises(NotFoundError):
            service.get_for(make_user(2), h.id)


class TestListForWithMembers:
    def test_admin_sees_all_houses_with_members(self, deps):
        service, *_ = deps
        admin = make_user(99, is_staff=True)

        u1 = make_user(1, email="a@x.com")
        u2 = make_user(2, email="b@x.com")
        h1 = service.request_create(u1, "101", "A")
        h2 = service.request_create(u2, "102", "A")
        service.approve(admin, h1.id)
        service.approve(admin, h2.id)

        result = service.list_for_with_members(admin)

        assert len(result) == 2
        house_ids = {item["household"].id for item in result}
        assert house_ids == {h1.id, h2.id}
        for item in result:
            assert len(item["members"]) == 1
            assert item["members"][0].status == HouseholdMembership.Status.ACTIVE

    def test_user_only_sees_own_house_with_members(self, deps):
        service, *_ = deps
        admin = make_user(99, is_staff=True)
        mine = make_user(1, email="mine@x.com")
        other = make_user(2, email="other@x.com")

        own_h = service.request_create(mine, "101", "A")
        other_h = service.request_create(other, "102", "A")
        service.approve(admin, own_h.id)
        service.approve(admin, other_h.id)

        result = service.list_for_with_members(mine)
        assert [i["household"].id for i in result] == [own_h.id]
        assert result[0]["members"][0].user_id == mine.id

    def test_status_filter_passes_through(self, deps):
        service, households, *_ = deps
        admin = make_user(99, is_staff=True)
        h = service.request_create(make_user(1, email="a@x.com"), "101", "A")
        service.request_create(make_user(2, email="b@x.com"), "102", "A")
        service.approve(admin, h.id)

        actives = service.list_for_with_members(
            admin, status=Household.Status.ACTIVE
        )
        assert [i["household"].id for i in actives] == [h.id]

    def test_empty_when_no_houses(self, deps):
        service, *_ = deps
        assert service.list_for_with_members(make_user(123)) == []


class TestSearchPublic:
    def test_finds_active_by_apartment_block(self, deps):
        service, households, *_ = deps
        service.request_create(make_user(1), "302", "A")
        results = service.search_public(TEST_CONDOMINIUM_CODE, "302", "A")
        assert len(results) == 1

    def test_excludes_archived(self, deps):
        service, households, *_ = deps
        h = service.request_create(make_user(1), "302", "A")
        households.update(h, {"status": Household.Status.ARCHIVED})
        assert service.search_public(TEST_CONDOMINIUM_CODE, "302", "A") == []
