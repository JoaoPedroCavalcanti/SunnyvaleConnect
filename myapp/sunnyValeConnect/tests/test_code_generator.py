"""Unit tests for RandomCodeGenerator."""

import pytest

from shared.infrastructure.code_generator import RandomCodeGenerator


pytestmark = pytest.mark.unit


class TestRandomCodeGenerator:
    def test_length_is_five(self):
        assert len(RandomCodeGenerator().five_digits()) == 5

    def test_only_digits(self):
        assert RandomCodeGenerator().five_digits().isdigit()

    def test_six_digits(self):
        code = RandomCodeGenerator().six_digits()
        assert len(code) == 6
        assert code.isdigit()
