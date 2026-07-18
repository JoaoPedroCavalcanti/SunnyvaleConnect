"""Unit tests for AuthService."""

import pytest

from units.models import Unit, UnitMembership
from units.tests.unit._fakes import (
    FakeCondominiumRepository,
    FakeUnitMembershipRepository,
    FakeUnitRepository,
    FakeUserRepository,
    TEST_CONDOMINIUM_CODE,
    make_unit,
    make_user,
)
from shared.tenant import build_tenant_username
from users.services.auth_service import (
    AuthService,
    KIND_DISABLED,
    KIND_INVALID,
    KIND_OK,
    KIND_PENDING,
    KIND_PENDING_EMAIL,
)


pytestmark = pytest.mark.unit


@pytest.fixture
def env():
    users = FakeUserRepository()
    memberships = FakeUnitMembershipRepository()
    units = FakeUnitRepository()
    auth = AuthService(
        user_repository=users,
        membership_repository=memberships,
    )
    return {
        "auth": auth,
        "users": users,
        "memberships": memberships,
        "units": units,
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

    def test_pending_when_inactive_with_pending_unit(self, env):
        user = _add(
            env["users"], 1, "secret", email="alice@example.com", is_active=False
        )
        unit = make_unit(
            1,
            kind=Unit.Kind.APARTMENT_BLOCK,
            apartment="501",
            block="A",
        )
        env["memberships"].create(
            {
                "unit": unit,
                "user": user,
                "role": UnitMembership.Role.OWNER,
                "status": UnitMembership.Status.PENDING_ADMIN,
            }
        )

        result = env["auth"].authenticate("alice@example.com", "secret")
        assert result["kind"] == KIND_PENDING
        assert result["unit"]["display_name"] == "Apt 501 / Block A"
        assert (
            result["unit"]["membership_status"]
            == UnitMembership.Status.PENDING_ADMIN
        )

    def test_pending_email_when_awaiting_verification(self, env):
        user = _add(
            env["users"], 1, "secret", email="alice@example.com", is_active=False
        )
        unit = make_unit(
            1,
            kind=Unit.Kind.APARTMENT_BLOCK,
            apartment="502",
            block="A",
        )
        env["memberships"].create(
            {
                "unit": unit,
                "user": user,
                "role": UnitMembership.Role.OWNER,
                "status": UnitMembership.Status.PENDING_EMAIL,
            }
        )

        result = env["auth"].authenticate("alice@example.com", "secret")
        assert result["kind"] == KIND_PENDING_EMAIL
        assert (
            result["unit"]["membership_status"]
            == UnitMembership.Status.PENDING_EMAIL
        )

    def test_disabled_when_inactive_without_pending(self, env):
        _add(env["users"], 1, "secret", email="alice@example.com", is_active=False)
        result = env["auth"].authenticate("alice@example.com", "secret")
        assert result["kind"] == KIND_DISABLED

    def test_platform_superuser_ok_without_condominium(self, env):
        _add(
            env["users"],
            1,
            "secret",
            email="super@platform.com",
            username="super",
            is_staff=True,
            is_superuser=True,
            is_active=True,
            condominium_id=None,
            condominium=None,
        )
        result = env["auth"].authenticate("super@platform.com", "secret")
        assert result["kind"] == KIND_OK
        assert result["condominium"] is None

    def test_non_superuser_without_condominium_invalid(self, env):
        _add(
            env["users"],
            1,
            "secret",
            email="orphan@example.com",
            is_active=True,
            condominium_id=None,
            condominium=None,
        )
        result = env["auth"].authenticate("orphan@example.com", "secret")
        assert result["kind"] == KIND_INVALID
