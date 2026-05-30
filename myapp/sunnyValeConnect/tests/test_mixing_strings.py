import pytest

from sunnyValeConnect.utils.mixing_and_unmixing_strings import (
    mix_strings,
    unmix_strings,
)


pytestmark = pytest.mark.unit


@pytest.mark.parametrize("original", ["42", "1", "123456", "abc"])
def test_mix_then_unmix_roundtrip(original):
    mix_code = "1783645917351"
    mixed = mix_strings(original, mix_code)

    assert mixed != original
    assert original in mixed
    assert unmix_strings(mixed, mix_code) == original


def test_mix_inserts_string_inside_mix_code():
    mix_code = "ABCDEFGHI"  # len 9 → insert_position = 3
    mixed = mix_strings("XYZ", mix_code)
    assert mixed == "ABCXYZDEFGHI"


def test_unmix_returns_empty_when_mixed_only_has_mix_code():
    mix_code = "ABCDEFGHI"
    assert unmix_strings(mix_code, mix_code) == ""
