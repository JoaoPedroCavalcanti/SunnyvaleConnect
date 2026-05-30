"""Unit tests for DefaultPasswordPolicy."""

import pytest

from shared.infrastructure.password_policy import DefaultPasswordPolicy


pytestmark = pytest.mark.unit


@pytest.fixture
def policy():
    return DefaultPasswordPolicy()


class TestDefaultPasswordPolicy:
    def test_valid_password_returns_empty_list(self, policy):
        assert policy.validate("StrongPass1!") == []

    def test_missing_upper(self, policy):
        errors = policy.validate("weakpass1!")
        assert "Password must contain at least one uppercase letter." in errors

    def test_too_short(self, policy):
        errors = policy.validate("Aa1!")
        assert "Password must be at least 8 characters long." in errors

    def test_missing_special(self, policy):
        errors = policy.validate("Strong123")
        assert any("special character" in e for e in errors)

    def test_all_errors_at_once(self, policy):
        errors = policy.validate("a")
        assert len(errors) == 3
