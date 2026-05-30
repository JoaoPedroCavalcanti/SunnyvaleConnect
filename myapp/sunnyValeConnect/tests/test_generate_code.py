import pytest

from sunnyValeConnect.utils.generate_checkin_and_checkout import (
    generate_five_digits_code,
)


pytestmark = pytest.mark.unit


def test_returns_exactly_five_characters():
    code = generate_five_digits_code()
    assert len(code) == 5


def test_only_digits():
    code = generate_five_digits_code()
    assert code.isdigit()


def test_is_a_string():
    assert isinstance(generate_five_digits_code(), str)


def test_codes_can_differ_between_calls():
    """Not guaranteed (it's random) but should very rarely collide; sample a few."""
    samples = {generate_five_digits_code() for _ in range(50)}
    # Birthday-style: with 100k possible codes and 50 samples, almost no duplicates
    assert len(samples) >= 40
