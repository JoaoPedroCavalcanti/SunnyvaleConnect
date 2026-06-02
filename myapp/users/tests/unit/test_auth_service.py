"""Unit tests for AuthService."""

from types import SimpleNamespace

import pytest

from households.tests.unit._fakes import (
    FakeHouseholdRepository,
    FakeMembershipRepository,
    FakeUserRepository,
    make_user,
)
from households.models import HouseholdMembership
from households.services.household_service import HouseholdService
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
    auth = AuthService(user_repository=users, membership_repository=memberships)
    household_service = HouseholdService(
        household_repository=households,
        membership_repository=memberships,
        user_repository=users,
        email_sender=email,
    )
    return {
        "auth": auth,
        "users": users,
        "memberships": memberships,
        "households": households,
        "household_service": household_service,
    }


def _add(users, pk, password, **overrides):
    user = make_user(pk, **overrides)
    user._password = password
    users._users[pk] = user
    return user


class TestAuthenticate:
    def test_ok_for_active_user(self, env):
        _add(env["users"], 1, "secret", username="alice", is_active=True)
        result = env["auth"].authenticate("alice", "secret")
        assert result["kind"] == KIND_OK

    def test_invalid_when_user_missing(self, env):
        assert env["auth"].authenticate("ghost", "x")["kind"] == KIND_INVALID

    def test_invalid_when_wrong_password(self, env):
        _add(env["users"], 1, "right", username="alice")
        assert (
            env["auth"].authenticate("alice", "wrong")["kind"] == KIND_INVALID
        )

    def test_pending_when_inactive_with_pending_household(self, env):
        user = _add(
            env["users"], 1, "secret", username="alice", is_active=False
        )
        # build a pending household for the user
        household = env["household_service"].request_create(user, "501", "A")

        result = env["auth"].authenticate("alice", "secret")
        assert result["kind"] == KIND_PENDING
        assert result["household"]["apartment"] == "501"
        assert (
            result["household"]["membership_status"]
            == HouseholdMembership.Status.PENDING_ADMIN
        )

    def test_disabled_when_inactive_without_pending(self, env):
        _add(env["users"], 1, "secret", username="alice", is_active=False)
        result = env["auth"].authenticate("alice", "secret")
        assert result["kind"] == KIND_DISABLED
