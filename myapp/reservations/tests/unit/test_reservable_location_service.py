from types import SimpleNamespace

import pytest

from reservations.repositories.reservable_location_repository import (
    IReservableLocationRepository,
)
from reservations.services.reservable_location_service import (
    ReservableLocationService,
)
from shared.exceptions import BusinessRuleError, PermissionDeniedError


pytestmark = pytest.mark.unit


class FakeLocationRepository(IReservableLocationRepository):
    def __init__(self):
        self.items = []

    def list_for_condominium(self, condominium_id, *, active_only=True):
        return [
            item
            for item in self.items
            if item.condominium_id == condominium_id
            and (item.is_active or not active_only)
        ]

    def get_by_id(self, pk):
        return next((item for item in self.items if item.id == pk), None)

    def exists_with_name(
        self, condominium_id, name, *, exclude_id=None
    ):
        return any(
            item.condominium_id == condominium_id
            and item.name.lower() == name.lower()
            and item.id != exclude_id
            for item in self.items
        )

    def create(self, data):
        item = SimpleNamespace(
            id=len(self.items) + 1,
            condominium_id=data["condominium"].id,
            is_active=True,
            **data,
        )
        self.items.append(item)
        return item

    def update(self, instance, data):
        for key, value in data.items():
            setattr(instance, key, value)
        return instance


class FakeCondominiumRepository:
    def __init__(self):
        self.condominium = SimpleNamespace(
            id=1, code="SUNNY001", is_active=True
        )

    def get_by_id(self, pk):
        return self.condominium if pk == 1 else None

    def get_by_code(self, code):
        return (
            self.condominium
            if code.upper() == self.condominium.code
            else None
        )


@pytest.fixture
def service():
    return ReservableLocationService(
        repository=FakeLocationRepository(),
        condominium_repository=FakeCondominiumRepository(),
    )


def _user(*, superuser=False, condominium_id=1):
    return SimpleNamespace(
        is_superuser=superuser,
        condominium_id=condominium_id,
    )


def test_only_platform_superuser_can_create(service):
    with pytest.raises(PermissionDeniedError):
        service.create(_user(), {"condominium_id": 1, "name": "Hall"})


def test_create_requires_exactly_one_tenant_target(service):
    with pytest.raises(BusinessRuleError):
        service.create(
            _user(superuser=True),
            {
                "condominium_id": 1,
                "condominium_code": "SUNNY001",
                "name": "Hall",
            },
        )


def test_case_insensitive_name_uniqueness_and_archive(service):
    admin = _user(superuser=True)
    item = service.create(
        admin, {"condominium_code": "SUNNY001", "name": " Party Hall "}
    )
    with pytest.raises(BusinessRuleError):
        service.create(
            admin, {"condominium_id": 1, "name": "party hall"}
        )
    service.archive(admin, item.id)
    assert item.is_active is False


def test_icon_is_saved_and_can_be_updated(service):
    admin = _user(superuser=True)
    item = service.create(
        admin,
        {
            "condominium_id": 1,
            "name": "Sports Court",
            "icon": " sports_soccer ",
        },
    )

    assert item.icon == "sports_soccer"
    service.update(admin, item.id, {"icon": "sports_basketball"})
    assert item.icon == "sports_basketball"


def test_tenant_user_lists_only_active_own_locations(service):
    admin = _user(superuser=True)
    active = service.create(
        admin, {"condominium_id": 1, "name": "Pool"}
    )
    archived = service.create(
        admin, {"condominium_id": 1, "name": "Hall"}
    )
    service.archive(admin, archived.id)
    assert service.list(_user()) == [active]
