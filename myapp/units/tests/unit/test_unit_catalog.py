"""Unit tests for public unit catalog grouping / filters."""

import pytest

from shared.exceptions import NotFoundError
from units.models import Unit
from units.services.unit_service import UnitService
from units.tests.unit._fakes import (
    FakeCondominiumRepository,
    FakeUnitMembershipRepository,
    FakeUnitRepository,
    TEST_CONDOMINIUM_CODE,
    make_user,
)
from units.unit_catalog import parse_apartment


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


class TestParseApartment:
    def test_floor_door_pattern(self):
        assert parse_apartment("1501") == ("15", "01")
        assert parse_apartment("101") == ("1", "01")
        assert parse_apartment("001") == ("0", "01")

    def test_flat_short_codes(self):
        assert parse_apartment("01") == (None, "01")
        assert parse_apartment("9") == (None, "9")
        assert parse_apartment("Casa 1") == (None, "Casa 1")


class TestListPublicCatalog:
    def test_groups_blocks_and_floors(self, deps):
        service, units, _ = deps
        for apt, block in (("101", "A"), ("102", "A"), ("201", "A"), ("101", "B")):
            units.create(
                {
                    "kind": Unit.Kind.APARTMENT_BLOCK,
                    "apartment": apt,
                    "block": block,
                    "status": Unit.Status.ACTIVE,
                    "condominium_id": 1,
                }
            )
        catalog = service.list_public(TEST_CONDOMINIUM_CODE)
        assert catalog["layout"] == "blocks"
        assert [b["block"] for b in catalog["blocks"]] == ["A", "B"]
        block_a = catalog["blocks"][0]
        assert [f["floor"] for f in block_a["floors"]] == ["1", "2"]
        floor_1 = block_a["floors"][0]
        assert [u["label"] for u in floor_1["units"]] == ["01", "02"]
        assert floor_1["units"][0]["apartment"] == "101"

    def test_filter_by_block_and_floor(self, deps):
        service, units, _ = deps
        for apt, block in (("1701", "A"), ("1702", "A"), ("1701", "B")):
            units.create(
                {
                    "kind": Unit.Kind.APARTMENT_BLOCK,
                    "apartment": apt,
                    "block": block,
                    "status": Unit.Status.ACTIVE,
                    "condominium_id": 1,
                }
            )
        catalog = service.list_public(
            TEST_CONDOMINIUM_CODE, block="a", floor="17"
        )
        assert len(catalog["blocks"]) == 1
        assert catalog["blocks"][0]["block"] == "A"
        assert len(catalog["blocks"][0]["floors"]) == 1
        labels = [u["label"] for u in catalog["blocks"][0]["floors"][0]["units"]]
        assert labels == ["01", "02"]

    def test_flat_houses_layout(self, deps):
        service, units, memberships = deps
        u1 = units.create(
            {
                "kind": Unit.Kind.APARTMENT,
                "apartment": "1",
                "status": Unit.Status.ACTIVE,
                "condominium_id": 1,
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
        memberships.create(
            {
                "unit": u1,
                "user": make_user(1),
                "role": "OWNER",
                "status": "ACTIVE",
            }
        )
        catalog = service.list_public(TEST_CONDOMINIUM_CODE)
        assert catalog["layout"] == "flat"
        assert [u["apartment"] for u in catalog["units"]] == ["1", "2"]
        assert catalog["units"][0]["is_occupied"] is True
        assert catalog["units"][1]["is_occupied"] is False

        filtered = service.list_public(TEST_CONDOMINIUM_CODE, apartment="2")
        assert [u["apartment"] for u in filtered["units"]] == ["2"]

    def test_tower_without_block(self, deps):
        service, units, _ = deps
        for apt in ("101", "102", "201"):
            units.create(
                {
                    "kind": Unit.Kind.APARTMENT,
                    "apartment": apt,
                    "status": Unit.Status.ACTIVE,
                    "condominium_id": 1,
                }
            )
        catalog = service.list_public(TEST_CONDOMINIUM_CODE)
        assert catalog["layout"] == "floors"
        assert [f["floor"] for f in catalog["floors"]] == ["1", "2"]

    def test_filters_endpoint_payload(self, deps):
        service, units, _ = deps
        for apt, block in (("101", "A"), ("1502", "A"), ("101", "B")):
            units.create(
                {
                    "kind": Unit.Kind.APARTMENT_BLOCK,
                    "apartment": apt,
                    "block": block,
                    "status": Unit.Status.ACTIVE,
                    "condominium_id": 1,
                }
            )
        units.create(
            {
                "kind": Unit.Kind.NAMED,
                "name": "Pool House",
                "status": Unit.Status.ACTIVE,
                "condominium_id": 1,
            }
        )
        opts = service.list_public_filters(TEST_CONDOMINIUM_CODE)
        assert opts["layout"] == "blocks"
        assert opts["filters"]["block"]["options"] == ["A", "B"]
        assert opts["filters"]["floor"]["options"] == ["1", "15"]
        assert opts["filters"]["floor"]["options_by_block"]["A"] == ["1", "15"]
        assert opts["filters"]["name"]["options"] == ["Pool House"]

    def test_invalid_code(self, deps):
        service, *_ = deps
        with pytest.raises(NotFoundError):
            service.list_public("NOPE")
