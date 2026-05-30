import pytest

from sunnyValeConnect.utils.passwordFunctions import (
    hasAtLeast8Characters,
    hasSpecialCharacter,
    hasUpperCase,
)


pytestmark = pytest.mark.unit


class TestHasUpperCase:
    @pytest.mark.parametrize("value", ["A", "abcD", "1A", "aaaaaaaaaaZ"])
    def test_true_when_any_upper(self, value):
        assert hasUpperCase(value) is True

    @pytest.mark.parametrize("value", ["", "abc", "1234", "!@#$", "a1!"])
    def test_false_otherwise(self, value):
        assert hasUpperCase(value) is False


class TestHasAtLeast8Characters:
    @pytest.mark.parametrize("value,expected", [
        ("a" * 7, False),
        ("a" * 8, True),
        ("a" * 9, True),
        ("", False),
    ])
    def test_length(self, value, expected):
        assert hasAtLeast8Characters(value) is expected


class TestHasSpecialCharacter:
    @pytest.mark.parametrize("value", ["abc!", "1@2", "_x_", "a b"])
    def test_true_when_special(self, value):
        assert hasSpecialCharacter(value) is True

    @pytest.mark.parametrize("value", ["abc", "ABC", "abc123", "ABCdef9"])
    def test_false_for_alnum(self, value):
        assert hasSpecialCharacter(value) is False
