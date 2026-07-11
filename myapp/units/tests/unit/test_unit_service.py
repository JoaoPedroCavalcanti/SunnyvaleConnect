"""Unit tests for UnitService."""

import pytest

from units.models import Unit
from units.services.unit_service import UnitService
from units.tests.unit._fakes import (
    FakeCondominiumRepository,
    FakeUnitMembershipRepository,
    FakeUnitRepository,
    TEST_CONDOMINIUM_CODE,
    make_user,
)
from shared.exceptions import (
    BusinessRuleError,
    NotFoundError,
    PermissionDeniedError,
)


pytestmark = pytest.mark.unit


@pytest.fixture
def deps():
    units = FakeUnitRepository()
    memberships = FakeUnitMembershipRepository()
    service = UnitService(
        unit_repository=units,
        membership_repository=memberships,
        condominium_repository=FakeCondominiumRepository(),
    )
    return service, units, memberships


class TestValidateKindFields:
    def test_named_requires_name(self, deps):
        service, *_ = deps
        with pytest.raises(BusinessRuleError) as exc:
            service.validate_kind_fields({"kind": Unit.Kind.NAMED, "name": ""})
        assert exc.value.field == "name"

    def test_apartment_requires_apartment(self, deps):
        service, *_ = deps
        with pytest.raises(BusinessRuleError):
            service.validate_kind_fields(
                {"kind": Unit.Kind.APARTMENT, "apartment": ""}
            )

    def test_apartment_block_requires_both(self, deps):
        service, *_ = deps
        with pytest.raises(BusinessRuleError):
            service.validate_kind_fields(
                {
                    "kind": Unit.Kind.APARTMENT_BLOCK,
                    "apartment": "101",
                    "block": "",
                }
            )


class TestCreate:
    def test_admin_creates_active_apartment_unit(self, deps):
        service, units, _ = deps
        admin = make_user(99, is_staff=True)
        unit = service.create(
            admin,
            {"kind": Unit.Kind.APARTMENT, "apartment": "302"},
        )
        assert unit.status == Unit.Status.ACTIVE
        assert unit.apartment == "302"
        assert len(units.list_all()) == 1

    def test_non_admin_cannot_create(self, deps):
        service, *_ = deps
        with pytest.raises(PermissionDeniedError):
            service.create(
                make_user(1),
                {"kind": Unit.Kind.APARTMENT, "apartment": "302"},
            )

    def test_duplicate_apartment_rejected(self, deps):
        service, *_ = deps
        admin = make_user(99, is_staff=True)
        service.create(admin, {"kind": Unit.Kind.APARTMENT, "apartment": "302"})
        with pytest.raises(BusinessRuleError) as exc:
            service.create(
                admin, {"kind": Unit.Kind.APARTMENT, "apartment": "302"}
            )
        assert exc.value.field == "kind"


class TestListPublic:
    def test_lists_active_units_with_occupancy(self, deps):
        service, units, memberships = deps
        unit = units.create(
            {
                "kind": Unit.Kind.APARTMENT,
                "apartment": "101",
                "status": Unit.Status.ACTIVE,
                "condominium_id": 1,
            }
        )
        owner = make_user(1)
        memberships.create(
            {
                "unit": unit,
                "user": owner,
                "role": "OWNER",
                "status": "ACTIVE",
            }
        )
        units.create(
            {
                "kind": Unit.Kind.APARTMENT,
                "apartment": "102",
                "status": Unit.Status.ACTIVE,
                "condominium_id": 1,
            }
        )

        results = service.list_public(TEST_CONDOMINIUM_CODE)
        assert len(results) == 2
        occupied = next(r for r in results if r["unit"].apartment == "101")
        vacant = next(r for r in results if r["unit"].apartment == "102")
        assert occupied["is_occupied"] is True
        assert vacant["is_occupied"] is False

    def test_invalid_condominium_code(self, deps):
        service, *_ = deps
        with pytest.raises(NotFoundError):
            service.list_public("INVALID")


class TestListAndGet:
    def test_admin_lists_all(self, deps):
        service, units, _ = deps
        admin = make_user(99, is_staff=True)
        units.create(
            {
                "kind": Unit.Kind.APARTMENT,
                "apartment": "101",
                "condominium_id": 1,
            }
        )
        units.create(
            {
                "kind": Unit.Kind.APARTMENT,
                "apartment": "102",
                "condominium_id": 1,
            }
        )
        assert len(service.list_for(admin)) == 2

    def test_get_for_404_when_not_member(self, deps):
        service, units, _ = deps
        unit = units.create(
            {
                "kind": Unit.Kind.APARTMENT,
                "apartment": "101",
                "condominium_id": 1,
            }
        )
        with pytest.raises(NotFoundError):
            service.get_for(make_user(2), unit.id)
