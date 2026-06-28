"""Unit tests for SignupService orchestration.

These exercise the wiring with the real Django UserService (using fake repos)
so the transaction boundary is also covered.
"""

import pytest

from condominiums.services.condominium_service import CondominiumService
from households.models import Household, HouseholdMembership
from households.services.household_service import HouseholdService
from households.services.membership_service import MembershipService
from households.services.signup_service import SignupService
from households.tests.unit._fakes import (
    FakeCondominiumRepository,
    FakeHouseholdRepository,
    FakeMembershipDecisionRepository,
    FakeMembershipRepository,
    FakeUserRepository,
    TEST_CONDOMINIUM_CODE,
    anon,
)
from shared.exceptions import BusinessRuleError
from shared.infrastructure.document_validators import (
    BrazilianCPFValidator,
    BrazilianPhoneValidator,
)
from shared.infrastructure.password_policy import DefaultPasswordPolicy
from shared.infrastructure.transactions import NullTransactionRunner
from shared.test_doubles.fakes import FakeCodeGenerator, FakeEmailSender
from users.services.user_service import UserService


# SignupService wraps its calls in ``transaction.atomic``, so a connection has
# to be available even though we inject in-memory fakes for every repository.
pytestmark = [pytest.mark.unit, pytest.mark.django_db]


VALID_CPF_A = "39053344705"
VALID_CPF_B = "12345678909"


@pytest.fixture
def env():
    households = FakeHouseholdRepository()
    memberships = FakeMembershipRepository()
    users = FakeUserRepository()
    email = FakeEmailSender()
    user_service = UserService(
        user_repository=users,
        password_policy=DefaultPasswordPolicy(),
        cpf_validator=BrazilianCPFValidator(),
        phone_validator=BrazilianPhoneValidator(),
    )
    condominiums = FakeCondominiumRepository()
    tx = NullTransactionRunner()
    household_service = HouseholdService(
        household_repository=households,
        membership_repository=memberships,
        user_repository=users,
        email_sender=email,
        transaction_runner=tx,
        condominium_repository=condominiums,
    )
    membership_service = MembershipService(
        membership_repository=memberships,
        household_repository=households,
        user_repository=users,
        email_sender=email,
        decision_repository=FakeMembershipDecisionRepository(),
        transaction_runner=tx,
    )
    condominium_service = CondominiumService(
        repository=condominiums,
        code_generator=FakeCodeGenerator(),
    )
    signup = SignupService(
        user_service=user_service,
        household_service=household_service,
        membership_service=membership_service,
        condominium_service=condominium_service,
    )
    return {
        "signup": signup,
        "households": households,
        "memberships": memberships,
        "users": users,
        "email": email,
    }


def _user_payload(**overrides):
    base = {
        "username": "joao",
        "password": "StrongPass1!",
        "full_name": "Joao",
        "birth_date": "1990-01-01",
        "cpf": VALID_CPF_A,
        "phone": "11987654321",
        "email": "joao@example.com",
        "apartment": "302",
        "block": "A",
        "condominium_code": TEST_CONDOMINIUM_CODE,
    }
    base.update(overrides)
    return base


class TestSignup:
    def test_without_household_request_creates_active_user(self, env):
        user = env["signup"].signup(anon(), _user_payload(), None)
        assert user.is_active is True

    def test_with_create_new_household_returns_pending_user(self, env):
        user = env["signup"].signup(
            anon(),
            _user_payload(),
            {"apartment": "302", "block": "A"},
        )
        assert user.is_active is False
        assert env["households"].list_all()[0].status == Household.Status.PENDING_ADMIN
        ms = env["memberships"].list_for_household(
            env["households"].list_all()[0].id
        )
        assert ms[0].status == HouseholdMembership.Status.PENDING_ADMIN
        assert ms[0].role == HouseholdMembership.Role.HOLDER

    def test_with_join_existing_creates_pending_resident(self, env):
        # holder creates the household first
        env["signup"].signup(
            anon(),
            _user_payload(),
            {"apartment": "302", "block": "A"},
        )
        household = env["households"].list_all()[0]
        household.status = Household.Status.ACTIVE  # simulate admin approval

        env["signup"].signup(
            anon(),
            _user_payload(
                username="maria",
                email="maria@example.com",
                cpf=VALID_CPF_B,
            ),
            {"household_id": household.id},
        )

        ms = env["memberships"].list_for_household(household.id)
        assert len(ms) == 2
        new_membership = next(
            m for m in ms if m.user.username.endswith(":maria")
        )
        assert new_membership.status == HouseholdMembership.Status.PENDING_HOLDER
        assert new_membership.role == HouseholdMembership.Role.RESIDENT

    def test_invalid_household_request_raises(self, env):
        with pytest.raises(BusinessRuleError):
            env["signup"].signup(anon(), _user_payload(), {})
