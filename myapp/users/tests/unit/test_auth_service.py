"""Unit tests for AuthService."""

import pytest

from households.tests.unit._fakes import (
    FakeCondominiumRepository,
    FakeHouseholdRepository,
    FakeMembershipRepository,
    FakeUserRepository,
    TEST_CONDOMINIUM_CODE,
    make_user,
)
from households.models import HouseholdMembership
from households.services.household_service import HouseholdService
from shared.infrastructure.transactions import NullTransactionRunner
from shared.tenant import build_tenant_username
from shared.test_doubles.fakes import FakeEmailSender
from users.services.auth_service import (
    AuthService,
    KIND_DISABLED,
    KIND_INVALID,
    KIND_OK,
    KIND_PENDING,
)


pytestmark = pytest.mark.unit


@pytest.fixture
def env():
    users = FakeUserRepository()
    memberships = FakeMembershipRepository()
    households = FakeHouseholdRepository()
    email = FakeEmailSender()
    condominiums = FakeCondominiumRepository()
    auth = AuthService(
        user_repository=users,
        membership_repository=memberships,
    )
    household_service = HouseholdService(
        household_repository=households,
        membership_repository=memberships,
        user_repository=users,
        email_sender=email,
        transaction_runner=NullTransactionRunner(),
        condominium_repository=condominiums,
    )
    return {
        "auth": auth,
        "users": users,
        "memberships": memberships,
        "households": households,
        "household_service": household_service,
    }


def _add(users, pk, password, **overrides):
    local_username = overrides.pop("username", "alice")
    email = overrides.pop("email", f"user{pk}@example.com")
    user = make_user(
        pk,
        username=build_tenant_username(TEST_CONDOMINIUM_CODE, local_username),
        email=email,
        **overrides,
    )
    user._password = password
    users._users[pk] = user
    return user


class TestAuthenticate:
    def test_ok_for_active_user(self, env):
        _add(env["users"], 1, "secret", email="alice@example.com", is_active=True)
        result = env["auth"].authenticate("alice@example.com", "secret")
        assert result["kind"] == KIND_OK

    def test_invalid_when_user_missing(self, env):
        assert env["auth"].authenticate("ghost@example.com", "x")["kind"] == KIND_INVALID

    def test_invalid_when_wrong_password(self, env):
        _add(env["users"], 1, "right", email="alice@example.com")
        assert env["auth"].authenticate("alice@example.com", "wrong")["kind"] == KIND_INVALID

    def test_pending_when_inactive_with_pending_household(self, env):
        user = _add(
            env["users"], 1, "secret", email="alice@example.com", is_active=False
        )
        household = env["household_service"].request_create(user, "501", "A")

        result = env["auth"].authenticate("alice@example.com", "secret")
        assert result["kind"] == KIND_PENDING
        assert result["household"]["apartment"] == "501"
        assert (
            result["household"]["membership_status"]
            == HouseholdMembership.Status.PENDING_ADMIN
        )

    def test_disabled_when_inactive_without_pending(self, env):
        _add(env["users"], 1, "secret", email="alice@example.com", is_active=False)
        result = env["auth"].authenticate("alice@example.com", "secret")
        assert result["kind"] == KIND_DISABLED
