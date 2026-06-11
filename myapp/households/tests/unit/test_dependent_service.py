"""Unit tests for DependentService."""

from datetime import date

import pytest

from households.services.dependent_service import DependentService
from households.services.household_service import HouseholdService
from households.services.membership_service import MembershipService
from households.tests.unit._fakes import (
    FakeDependentRepository,
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
from shared.infrastructure.document_validators import BrazilianCPFValidator
from shared.infrastructure.transactions import NullTransactionRunner
from shared.test_doubles.fakes import FakeEmailSender


pytestmark = pytest.mark.unit


VALID_CPF = "39053344705"


@pytest.fixture
def fixtures():
    households = FakeHouseholdRepository()
    memberships = FakeMembershipRepository()
    users = FakeUserRepository()
    dependents = FakeDependentRepository()
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
    service = DependentService(
        dependent_repository=dependents,
        membership_repository=memberships,
        household_repository=households,
        user_repository=users,
        cpf_validator=BrazilianCPFValidator(),
    )

    holder = make_user(1, email="h@x.com")
    household = household_service.request_create(holder, "302", "A")
    household_service.approve(make_user(99, is_staff=True), household.id)

    outsider = make_user(2)

    return {
        "service": service,
        "membership_service": membership_service,
        "households": households,
        "memberships": memberships,
        "dependents": dependents,
        "users": users,
        "holder": holder,
        "outsider": outsider,
        "household": household,
    }


def _payload(**overrides):
    base = {
        "full_name": "Filho da Silva",
        "birth_date": date(2010, 1, 1),
        "relationship": "filho",
        "cpf": "",
    }
    base.update(overrides)
    return base


class TestCreate:
    def test_active_member_creates(self, fixtures):
        service = fixtures["service"]
        d = service.create(
            fixtures["holder"], fixtures["household"].id, _payload()
        )
        assert d.full_name == "Filho da Silva"

    def test_non_member_blocked(self, fixtures):
        service = fixtures["service"]
        with pytest.raises(PermissionDeniedError):
            service.create(
                fixtures["outsider"], fixtures["household"].id, _payload()
            )

    def test_invalid_cpf_rejected(self, fixtures):
        service = fixtures["service"]
        with pytest.raises(BusinessRuleError) as exc:
            service.create(
                fixtures["holder"],
                fixtures["household"].id,
                _payload(cpf="11111111111"),
            )
        assert exc.value.field == "cpf"

    def test_cpf_conflict_with_user_rejected(self, fixtures):
        service = fixtures["service"]
        fixtures["holder"].cpf = VALID_CPF
        fixtures["users"]._users[fixtures["holder"].id] = fixtures["holder"]
        with pytest.raises(BusinessRuleError) as exc:
            service.create(
                fixtures["holder"],
                fixtures["household"].id,
                _payload(cpf=VALID_CPF),
            )
        assert exc.value.field == "cpf"

    def test_unknown_household_404(self, fixtures):
        service = fixtures["service"]
        with pytest.raises(NotFoundError):
            service.create(fixtures["holder"], 9999, _payload())


class TestListResidents:
    def test_member_sees_members_first_then_dependents(self, fixtures):
        service = fixtures["service"]
        service.create(
            fixtures["holder"], fixtures["household"].id, _payload(full_name="A")
        )
        service.create(
            fixtures["holder"], fixtures["household"].id, _payload(full_name="B")
        )

        items = service.list_residents(
            fixtures["holder"], fixtures["household"].id
        )

        types = [i["type"] for i in items]
        assert types == ["household", "dependent", "dependent"], items
        assert items[0]["obj"].user_id == fixtures["holder"].id

    def test_admin_can_list_any_house(self, fixtures):
        service = fixtures["service"]
        admin = make_user(99, is_staff=True)
        items = service.list_residents(admin, fixtures["household"].id)
        assert any(i["type"] == "household" for i in items)

    def test_outsider_blocked(self, fixtures):
        service = fixtures["service"]
        with pytest.raises(PermissionDeniedError):
            service.list_residents(
                fixtures["outsider"], fixtures["household"].id
            )

    def test_unknown_household_404(self, fixtures):
        service = fixtures["service"]
        with pytest.raises(NotFoundError):
            service.list_residents(fixtures["holder"], 9999)

    def test_only_active_dependents_included(self, fixtures):
        service = fixtures["service"]
        kept = service.create(
            fixtures["holder"], fixtures["household"].id, _payload(full_name="K")
        )
        gone = service.create(
            fixtures["holder"], fixtures["household"].id, _payload(full_name="G")
        )
        service.delete(fixtures["holder"], gone.id)

        items = service.list_residents(
            fixtures["holder"], fixtures["household"].id
        )
        dep_ids = [i["obj"].id for i in items if i["type"] == "dependent"]
        assert dep_ids == [kept.id]


class TestUpdateAndDelete:
    def test_update_name(self, fixtures):
        service = fixtures["service"]
        d = service.create(
            fixtures["holder"], fixtures["household"].id, _payload()
        )
        result = service.update(fixtures["holder"], d.id, {"full_name": "New"})
        assert result.full_name == "New"

    def test_soft_delete(self, fixtures):
        service = fixtures["service"]
        d = service.create(
            fixtures["holder"], fixtures["household"].id, _payload()
        )
        service.delete(fixtures["holder"], d.id)
        assert d.is_active is False

    def test_delete_404_for_inactive(self, fixtures):
        service = fixtures["service"]
        d = service.create(
            fixtures["holder"], fixtures["household"].id, _payload()
        )
        service.delete(fixtures["holder"], d.id)
        with pytest.raises(NotFoundError):
            service.delete(fixtures["holder"], d.id)
