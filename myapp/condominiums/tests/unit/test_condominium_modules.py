"""Unit tests for condominium module catalog helpers and create defaults."""

from types import SimpleNamespace

import pytest

from condominiums.modules import (
    ALL_MODULE_KEYS,
    default_enabled_modules,
    normalize_enabled_modules,
)
from condominiums.services.condominium_service import CondominiumService
from shared.exceptions import BusinessRuleError, PermissionDeniedError
from shared.test_doubles.fakes import FakeCodeGenerator


pytestmark = pytest.mark.unit


class FakeCondoRepo:
    def __init__(self):
        self.created = []
        self._codes = set()

    def get_by_code(self, code):
        return None

    def list_all(self):
        return []

    def exists_with_code(self, code):
        return code in self._codes

    def create(self, data):
        item = SimpleNamespace(id=1, **data)
        self.created.append(item)
        self._codes.add(data["code"])
        return item


def test_normalize_preserves_catalog_order_and_rejects_unknown():
    assert normalize_enabled_modules(
        ["delivery_notification", "reservations"]
    ) == ["reservations", "delivery_notification"]
    with pytest.raises(ValueError):
        normalize_enabled_modules(["not_a_module"])


def test_create_defaults_to_all_modules():
    repo = FakeCondoRepo()
    service = CondominiumService(
        repository=repo, code_generator=FakeCodeGenerator()
    )
    superuser = SimpleNamespace(is_superuser=True)
    created = service.create(superuser, {"name": "Chacon"})
    assert created.enabled_modules == default_enabled_modules()
    assert set(created.enabled_modules) == set(ALL_MODULE_KEYS)


def test_create_accepts_subset_and_rejects_resident():
    repo = FakeCondoRepo()
    service = CondominiumService(
        repository=repo, code_generator=FakeCodeGenerator()
    )
    superuser = SimpleNamespace(is_superuser=True)
    created = service.create(
        superuser,
        {
            "name": "Chacon",
            "enabled_modules": ["visitor_access", "sunny_vale_news"],
        },
    )
    assert created.enabled_modules == [
        "visitor_access",
        "sunny_vale_news",
    ]
    with pytest.raises(PermissionDeniedError):
        service.create(SimpleNamespace(is_superuser=False), {"name": "X"})
    with pytest.raises(BusinessRuleError):
        service.create(
            superuser,
            {"name": "Y", "enabled_modules": ["nope"]},
        )
