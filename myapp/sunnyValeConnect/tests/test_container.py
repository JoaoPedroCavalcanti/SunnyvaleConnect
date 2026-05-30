"""Tests for the DI container itself."""

import pytest

from shared.container import Container, container


pytestmark = pytest.mark.unit


class TestContainer:
    def test_is_singleton(self):
        assert Container() is container

    def test_override_replaces_provider(self):
        marker = object()
        container.override("email_sender", marker)
        try:
            assert container.email_sender is marker
        finally:
            container.reset()

    def test_reset_clears_overrides(self):
        container.override("email_sender", object())
        container.reset()
        assert container.email_sender is not None

    def test_lazy_singleton(self):
        a = container.email_sender
        b = container.email_sender
        assert a is b
