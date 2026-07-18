"""Unit tests for units SignupService orchestration."""

from datetime import date

import pytest

from condominiums.services.condominium_service import CondominiumService
from units.models import UnitMembership
from units.services.signup_service import (
    KIND_CREATED,
    KIND_PENDING_EMAIL,
    SignupService,
)
from units.services.unit_membership_service import UnitMembershipService
from units.services.unit_service import UnitService
from units.tests.unit._fakes import (
    FakeCondominiumRepository,
    FakeUnitMembershipDecisionRepository,
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
from shared.test_doubles.fakes import FakeCache, FakeCodeGenerator, FakeEmailSender
from users.services.user_service import UserService


pytestmark = [pytest.mark.unit, pytest.mark.django_db]

VALID_CPF_A = "39053344705"
VALID_CPF_B = "12345678909"


@pytest.fixture
def env():
    units = FakeUnitRepository()
    memberships = FakeUnitMembershipRepository()
    decisions = FakeUnitMembershipDecisionRepository()
    users = FakeUserRepository()
    email = FakeEmailSender()
    cache = FakeCache()
    codes = FakeCodeGenerator("112233")
    tx = NullTransactionRunner()
    user_service = UserService(
        user_repository=users,
        password_policy=DefaultPasswordPolicy(),
        cpf_validator=BrazilianCPFValidator(),
        phone_validator=BrazilianPhoneValidator(),
        membership_repository=memberships,
        transaction_runner=tx,
    )
    condominiums = FakeCondominiumRepository()
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
        decision_repository=decisions,
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
        unit_repository=units,
        cache=cache,
        code_generator=codes,
        email_sender=email,
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
        "email": email,
        "cache": cache,
        "codes": codes,
        "unit": unit,
        "unit_service": unit_service,
    }


def _user_payload(**overrides):
    base = {
        "username": "joao",
        "password": "StrongPass1!",
        "full_name": "Joao",
        "birth_date": date(1990, 1, 1),
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
        result = env["signup"].signup(anon(), _user_payload(), None)
        assert result["kind"] == KIND_CREATED
        assert result["user"].is_active is True

    def test_with_unit_request_does_not_persist_until_otp(self, env):
        result = env["signup"].signup(
            anon(),
            _user_payload(),
            {"unit_id": env["unit"].id},
        )
        assert result["kind"] == KIND_PENDING_EMAIL
        assert result["email"] == "joao@example.com"
        assert list(env["users"].list_all()) == []
        assert env["memberships"].list_for_unit(env["unit"].id) == []
        assert any(
            s["kind"] == "email_verification" for s in env["email"].sent
        )

    def test_confirm_email_creates_user_and_pending_membership(self, env):
        env["users"].admin_emails = ["admin@example.com"]
        env["signup"].signup(
            anon(),
            _user_payload(),
            {"unit_id": env["unit"].id},
        )
        confirmed = env["signup"].confirm_email(
            "joao@example.com", env["codes"].six_digits()
        )
        user = confirmed["user"]
        assert user.is_active is False
        ms = env["memberships"].list_for_unit(env["unit"].id)
        assert len(ms) == 1
        assert ms[0].status == UnitMembership.Status.PENDING_ADMIN
        assert ms[0].role == UnitMembership.Role.OWNER
        assert any(
            s["kind"] == "household_creation_request" for s in env["email"].sent
        )

    def test_confirm_email_rejects_wrong_code(self, env):
        env["signup"].signup(
            anon(),
            _user_payload(),
            {"unit_id": env["unit"].id},
        )
        with pytest.raises(BusinessRuleError):
            env["signup"].confirm_email("joao@example.com", "000000")
        assert list(env["users"].list_all()) == []

    def test_resend_rate_limited(self, env):
        env["signup"].signup(
            anon(),
            _user_payload(),
            {"unit_id": env["unit"].id},
        )
        env["signup"].resend_verification("joao@example.com")
        with pytest.raises(BusinessRuleError):
            env["signup"].resend_verification("joao@example.com")

    def test_invalid_unit_request_raises(self, env):
        with pytest.raises(BusinessRuleError):
            env["signup"].signup(anon(), _user_payload(), {})

    def test_admin_provision_activates_membership_immediately(self, env):
        admin = make_user(99, is_staff=True)
        result = env["signup"].signup(
            admin,
            _user_payload(username="maria", email="maria@example.com", cpf=VALID_CPF_B),
            {"unit_id": env["unit"].id},
        )
        assert result["kind"] == KIND_CREATED
        assert result["user"].is_active is True
        ms = env["memberships"].list_for_unit(env["unit"].id)
        assert ms[0].status == UnitMembership.Status.ACTIVE

    def test_admin_cannot_create_resident_without_unit(self, env):
        admin = make_user(99, is_staff=True)

        with pytest.raises(BusinessRuleError) as exc:
            env["signup"].signup(admin, _user_payload(), None)

        assert exc.value.field == "unit_request"
        assert list(env["users"].list_all()) == []
