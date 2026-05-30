"""Unit tests for SecretStringMixer."""

import pytest

from shared.infrastructure.string_mixer import SecretStringMixer


pytestmark = pytest.mark.unit


@pytest.fixture
def mixer():
    return SecretStringMixer(secret="1783645917351")


class TestSecretStringMixer:
    @pytest.mark.parametrize("value", ["1", "42", "abc", "00000"])
    def test_round_trip(self, mixer, value):
        assert mixer.unmix(mixer.mix(value)) == value

    def test_mix_inserts_value_inside_secret(self, mixer):
        mixed = mixer.mix("X")
        assert "X" in mixed
        assert len(mixed) == len("1783645917351") + 1
