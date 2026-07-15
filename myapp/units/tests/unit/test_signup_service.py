"""Unit tests for units SignupService orchestration."""

import pytest

from condominiums.services.condominium_service import CondominiumService
from units.models import UnitMembership
from units.services.signup_service import SignupService
from units.services.unit_membership_service import UnitMembershipService
from units.services.unit_service import UnitService
from units.tests.unit._fakes import (
    FakeCondominiumRepository,
    FakeUnitMembershipRepository,
    FakeUnitRepository,
    FakeUserRepository,
    TEST_CONDOMINIUM_CODE,
    anon,
    make_user,
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


pytestmark = [pytest.mark.unit, pytest.mark.django_db]

VALID_CPF_A = "39053344705"
VALID_CPF_B = "12345678909"


@pytest.fixture
def env():
    units = FakeUnitRepository()
    memberships = FakeUnitMembershipRepository()
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
    unit_service = UnitService(
        unit_repository=units,
        membership_repository=memberships,
        condominium_repository=condominiums,
    )
    membership_service = UnitMembershipService(
        membership_repository=memberships,
        unit_repository=units,
        user_repository=users,
        email_sender=email,
        transaction_runner=tx,
    )
    condominium_service = CondominiumService(
        repository=condominiums,
        code_generator=FakeCodeGenerator(),
    )
    signup = SignupService(
        user_service=user_service,
        membership_service=membership_service,
        condominium_service=condominium_service,
    )
    unit = unit_service.create(
        make_user(99, is_staff=True),
        {"kind": "APARTMENT", "apartment": "302"},
    )
    return {
        "signup": signup,
        "units": units,
        "memberships": memberships,
        "users": users,
        "unit": unit,
        "unit_service": unit_service,
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
    def test_without_unit_request_creates_active_user(self, env):
        user = env["signup"].signup(anon(), _user_payload(), None)
        assert user.is_active is True

    def test_with_unit_request_creates_pending_user(self, env):
        user = env["signup"].signup(
            anon(),
            _user_payload(),
            {"unit_id": env["unit"].id},
        )
        assert user.is_active is False
        ms = env["memberships"].list_for_unit(env["unit"].id)
        assert len(ms) == 1
        assert ms[0].status == UnitMembership.Status.PENDING_ADMIN
        assert ms[0].role == UnitMembership.Role.OWNER

    def test_invalid_unit_request_raises(self, env):
        with pytest.raises(BusinessRuleError):
            env["signup"].signup(anon(), _user_payload(), {})

    def test_admin_provision_activates_membership_immediately(self, env):
        admin = make_user(99, is_staff=True)
        user = env["signup"].signup(
            admin,
            _user_payload(username="maria", email="maria@example.com", cpf=VALID_CPF_B),
            {"unit_id": env["unit"].id},
        )
        assert user.is_active is True
        ms = env["memberships"].list_for_unit(env["unit"].id)
        assert ms[0].status == UnitMembership.Status.ACTIVE

    def test_admin_cannot_create_resident_without_unit(self, env):
        admin = make_user(99, is_staff=True)

        with pytest.raises(BusinessRuleError) as exc:
            env["signup"].signup(admin, _user_payload(), None)

        assert exc.value.field == "unit_request"
        assert list(env["users"].list_all()) == []
