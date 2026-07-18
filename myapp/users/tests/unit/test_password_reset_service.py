"""Unit tests for PasswordResetService."""

import pytest

from shared.exceptions import BusinessRuleError
from shared.infrastructure.password_policy import DefaultPasswordPolicy
from shared.test_doubles.fakes import FakeCache, FakeCodeGenerator, FakeEmailSender
from units.tests.unit._fakes import FakeUserRepository, make_user
from users.services.password_reset_service import PasswordResetService


pytestmark = pytest.mark.unit


@pytest.fixture
def env():
    users = FakeUserRepository()
    cache = FakeCache()
    codes = FakeCodeGenerator("654321")
    email = FakeEmailSender()
    service = PasswordResetService(
        user_repository=users,
        cache=cache,
        code_generator=codes,
        email_sender=email,
        password_policy=DefaultPasswordPolicy(),
    )
    user = make_user(1, email="alice@example.com", full_name="Alice")
    user._password = "OldPass1!"
    users._users[1] = user
    return {
        "service": service,
        "users": users,
        "cache": cache,
        "codes": codes,
        "email": email,
        "user": user,
    }


class TestPasswordReset:
    def test_request_sends_otp_for_existing_user(self, env):
        env["service"].request_reset("alice@example.com")
        assert any(s["kind"] == "password_reset" for s in env["email"].sent)
        assert env["cache"].get("password_reset:alice@example.com") == "654321"

    def test_request_unknown_email_is_silent(self, env):
        env["service"].request_reset("ghost@example.com")
        assert env["email"].sent == []

    def test_confirm_updates_password(self, env):
        env["service"].request_reset("alice@example.com")
        env["service"].confirm_reset(
            "alice@example.com", "654321", "NewPass1!"
        )
        assert env["user"]._password == "NewPass1!"
        assert env["cache"].get("password_reset:alice@example.com") is None

    def test_confirm_rejects_wrong_code(self, env):
        env["service"].request_reset("alice@example.com")
        with pytest.raises(BusinessRuleError):
            env["service"].confirm_reset(
                "alice@example.com", "000000", "NewPass1!"
            )
        assert env["user"]._password == "OldPass1!"

    def test_confirm_rejects_weak_password(self, env):
        env["service"].request_reset("alice@example.com")
        with pytest.raises(BusinessRuleError) as exc:
            env["service"].confirm_reset("alice@example.com", "654321", "a")
        assert exc.value.field == "new_password"

    def test_resend_rate_limited(self, env):
        env["service"].request_reset("alice@example.com")
        env["service"].resend_code("alice@example.com")
        with pytest.raises(BusinessRuleError):
            env["service"].resend_code("alice@example.com")
