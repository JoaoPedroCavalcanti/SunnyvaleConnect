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

    def test_duplicate_apartment_block_case_insensitive(self, deps):
        service, *_ = deps
        admin = make_user(99, is_staff=True)
        created = service.create(
            admin,
            {
                "kind": Unit.Kind.APARTMENT_BLOCK,
                "apartment": "1101",
                "block": "A",
            },
        )
        assert created.apartment == "1101"
        assert created.block == "A"
        with pytest.raises(BusinessRuleError):
            service.create(
                admin,
                {
                    "kind": Unit.Kind.APARTMENT_BLOCK,
                    "apartment": "1101",
                    "block": "a",
                },
            )
        with pytest.raises(BusinessRuleError):
            service.create(
                admin,
                {
                    "kind": Unit.Kind.APARTMENT_BLOCK,
                    "apartment": "1101",
                    "block": "A",
                },
            )

    def test_bulk_skips_case_insensitive_duplicates(self, deps):
        service, units, _ = deps
        superuser = make_user(1, is_staff=True, is_superuser=True)
        units.create(
            {
                "kind": Unit.Kind.APARTMENT_BLOCK,
                "apartment": "101",
                "block": "a",
                "condominium_id": 1,
            }
        )
        result = service.bulk_provision(
            superuser,
            {
                "condominium_id": 1,
                "blocks": [{"block": "A", "floors": 1, "units": ["01"]}],
            },
        )
        assert result.created_count == 0
        assert result.skipped_count == 1


class TestListPublic:
    def test_lists_active_units_with_occupancy(self, deps):
        service, units, memberships = deps
        unit = units.create(
            {
                "kind": Unit.Kind.APARTMENT,
                "apartment": "1",
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
                "apartment": "2",
                "status": Unit.Status.ACTIVE,
                "condominium_id": 1,
            }
        )

        results = service.list_public(TEST_CONDOMINIUM_CODE)
        assert results["layout"] == "flat"
        by_apt = {u["apartment"]: u for u in results["units"]}
        assert by_apt["1"]["is_occupied"] is True
        assert by_apt["2"]["is_occupied"] is False

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


class TestBulkProvision:
    def test_expands_blocks_floors_and_units(self, deps):
        service, units, _ = deps
        superuser = make_user(1, is_staff=True, is_superuser=True)
        result = service.bulk_provision(
            superuser,
            {
                "condominium_code": TEST_CONDOMINIUM_CODE,
                "blocks": [
                    {"block": "A", "floors": 2, "units": ["01", "02"]},
                    {"block": "B", "floors": 1, "units": ["01"]},
                ],
                "named_units": ["Salão"],
            },
        )
        # A: 2 floors × 2 = 4; B: 1 × 1 = 1; named: 1 → 6
        assert result.created_count == 6
        assert result.skipped_count == 0
        apts = {(u.apartment, u.block) for u in result.created if u.block}
        assert ("101", "A") in apts
        assert ("202", "A") in apts
        assert ("101", "B") in apts
        assert len(units.list_all()) == 6

    def test_skips_existing_by_default(self, deps):
        service, units, _ = deps
        superuser = make_user(1, is_staff=True, is_superuser=True)
        units.create(
            {
                "kind": Unit.Kind.APARTMENT_BLOCK,
                "apartment": "101",
                "block": "A",
                "condominium_id": 1,
            }
        )
        result = service.bulk_provision(
            superuser,
            {
                "condominium_id": 1,
                "blocks": [
                    {"block": "A", "floors": 1, "units": ["01", "02"]},
                ],
            },
        )
        assert result.created_count == 1
        assert result.skipped_count == 1
        assert result.created[0].apartment == "102"

    def test_condo_admin_without_superuser_denied(self, deps):
        service, *_ = deps
        with pytest.raises(PermissionDeniedError):
            service.bulk_provision(
                make_user(99, is_staff=True, is_superuser=False),
                {
                    "condominium_code": TEST_CONDOMINIUM_CODE,
                    "blocks": [{"block": "A", "floors": 1, "units": ["01"]}],
                },
            )

    def test_chacon_scale_counts(self, deps):
        service, *_ = deps
        superuser = make_user(1, is_staff=True, is_superuser=True)
        result = service.bulk_provision(
            superuser,
            {
                "condominium_code": TEST_CONDOMINIUM_CODE,
                "blocks": [
                    {"block": "A", "floors": 15, "units": ["01", "02"]},
                    {"block": "B", "floors": 18, "units": ["01", "02"]},
                    {"block": "C", "floors": 15, "units": ["01", "02"]},
                ],
            },
        )
        assert result.created_count == 15 * 2 + 18 * 2 + 15 * 2

    def test_tower_without_block(self, deps):
        service, *_ = deps
        superuser = make_user(1, is_staff=True, is_superuser=True)
        result = service.bulk_provision(
            superuser,
            {
                "condominium_code": TEST_CONDOMINIUM_CODE,
                "towers": [{"floors": 17, "units": ["01", "02"]}],
            },
        )
        assert result.created_count == 34
        assert all(u.kind == Unit.Kind.APARTMENT for u in result.created)
        assert all(u.block == "" for u in result.created)
        apts = {u.apartment for u in result.created}
        assert "101" in apts
        assert "1702" in apts

    def test_house_number_range(self, deps):
        service, *_ = deps
        superuser = make_user(1, is_staff=True, is_superuser=True)
        result = service.bulk_provision(
            superuser,
            {
                "condominium_code": TEST_CONDOMINIUM_CODE,
                "number_range": {"start": 1, "end": 90},
            },
        )
        assert result.created_count == 90
        assert result.created[0].apartment == "1"
        assert result.created[-1].apartment == "90"

    def test_named_blocks_like_arabaiana(self, deps):
        service, *_ = deps
        superuser = make_user(1, is_staff=True, is_superuser=True)
        result = service.bulk_provision(
            superuser,
            {
                "condominium_code": TEST_CONDOMINIUM_CODE,
                "blocks": [
                    {
                        "block": "Arabaiana",
                        "floors": 14,
                        "units": ["01", "02", "03", "04", "05", "06", "07"],
                    }
                ],
            },
        )
        assert result.created_count == 14 * 7
        assert result.created[0].block == "ARABAIANA"
        assert result.created[0].kind == Unit.Kind.APARTMENT_BLOCK
