"""Business rules for Unit lifecycle (create / list / peek)."""

from abc import ABC, abstractmethod

from condominiums.repositories.condominium_repository import ICondominiumRepository
from units.models import Unit
from units.repositories.unit_membership_repository import IUnitMembershipRepository
from units.repositories.unit_repository import IUnitRepository
from shared.exceptions import (
    BusinessRuleError,
    NotFoundError,
    PermissionDeniedError,
)
from shared.tenant import assert_same_condominium, require_condominium_id


class IUnitService(ABC):
    @abstractmethod
    def list_public(self, condominium_code: str) -> list[dict]: ...

    @abstractmethod
    def list_for(self, user, status: str | None = None): ...

    @abstractmethod
    def list_for_with_members(
        self, user, status: str | None = None
    ) -> list[dict]: ...

    @abstractmethod
    def get_for(self, user, pk: int) -> Unit: ...

    @abstractmethod
    def peek(self, pk: int, *, condominium_id: int) -> Unit | None: ...

    @abstractmethod
    def create(self, admin, payload: dict) -> Unit: ...

    @abstractmethod
    def validate_kind_fields(self, payload: dict) -> dict: ...


class UnitService(IUnitService):
    def __init__(
        self,
        unit_repository: IUnitRepository,
        membership_repository: IUnitMembershipRepository,
        condominium_repository: ICondominiumRepository,
    ):
        self._repo = unit_repository
        self._memberships = membership_repository
        self._condominiums = condominium_repository

    def list_public(self, condominium_code: str) -> list[dict]:
        condominium = self._condominiums.get_by_code(condominium_code)
        if not condominium or not condominium.is_active:
            raise NotFoundError("Invalid or inactive condominium code.")
        units = list(
            self._repo.list_all(
                status=Unit.Status.ACTIVE, condominium_id=condominium.id
            )
        )
        return [self._with_occupancy(u) for u in units]

    def list_for(self, user, status=None):
        condominium_id = require_condominium_id(user)
        if getattr(user, "is_staff", False):
            return list(
                self._repo.list_all(status=status, condominium_id=condominium_id)
            )
        memberships = self._memberships.list_active_for_user(user.id)
        seen: dict[int, Unit] = {}
        for m in memberships:
            unit = m.unit
            if status and unit.status != status:
                continue
            seen[unit.id] = unit
        return list(seen.values())

    def list_for_with_members(self, user, status=None) -> list[dict]:
        units = list(self.list_for(user, status=status))
        if not units:
            return []
        memberships = self._memberships.list_active_for_units(
            [u.id for u in units]
        )
        grouped: dict[int, list] = {u.id: [] for u in units}
        for m in memberships:
            grouped.setdefault(m.unit_id, []).append(m)
        return [
            {"unit": u, "members": grouped.get(u.id, [])} for u in units
        ]

    def get_for(self, user, pk):
        instance = self._repo.get_by_id(pk)
        if not instance:
            raise NotFoundError("No unit matches the given query.")
        assert_same_condominium(user, instance.condominium_id)
        if getattr(user, "is_staff", False):
            return instance
        if not self._memberships.get_for_user_and_unit(user.id, instance.id):
            raise NotFoundError("No unit matches the given query.")
        return instance

    def peek(self, pk, *, condominium_id: int):
        instance = self._repo.get_by_id(pk)
        if not instance or instance.condominium_id != condominium_id:
            return None
        return instance

    def create(self, admin, payload: dict) -> Unit:
        if not getattr(admin, "is_staff", False):
            raise PermissionDeniedError("Only staff can create units.")

        condominium_id = require_condominium_id(admin)
        normalized = self.validate_kind_fields(payload)

        if self._duplicate_exists(condominium_id, normalized):
            raise BusinessRuleError(
                "A unit with these identifiers already exists.",
                field="kind",
            )

        return self._repo.create(
            {
                "kind": normalized["kind"],
                "name": normalized.get("name", ""),
                "apartment": normalized.get("apartment", ""),
                "block": normalized.get("block", ""),
                "status": Unit.Status.ACTIVE,
                "condominium_id": condominium_id,
            }
        )

    def validate_kind_fields(self, payload: dict) -> dict:
        kind = payload.get("kind")
        if kind not in Unit.Kind.values:
            raise BusinessRuleError("Invalid unit kind.", field="kind")

        name = (payload.get("name") or "").strip()
        apartment = (payload.get("apartment") or "").strip()
        block = (payload.get("block") or "").strip()

        if kind == Unit.Kind.NAMED:
            if not name:
                raise BusinessRuleError("name is required.", field="name")
            if apartment or block:
                raise BusinessRuleError(
                    "apartment and block must be empty for NAMED units.",
                    field="apartment",
                )
            return {"kind": kind, "name": name, "apartment": "", "block": ""}

        if kind == Unit.Kind.APARTMENT:
            if not apartment:
                raise BusinessRuleError(
                    "apartment is required.", field="apartment"
                )
            if name or block:
                raise BusinessRuleError(
                    "name and block must be empty for APARTMENT units.",
                    field="name",
                )
            return {
                "kind": kind,
                "name": "",
                "apartment": apartment,
                "block": "",
            }

        if not apartment:
            raise BusinessRuleError("apartment is required.", field="apartment")
        if not block:
            raise BusinessRuleError("block is required.", field="block")
        if name:
            raise BusinessRuleError(
                "name must be empty for APARTMENT_BLOCK units.", field="name"
            )
        return {
            "kind": kind,
            "name": "",
            "apartment": apartment,
            "block": block,
        }

    def _duplicate_exists(self, condominium_id: int, normalized: dict) -> bool:
        kind = normalized["kind"]
        if kind == Unit.Kind.NAMED:
            return (
                self._repo.get_by_name(
                    normalized["name"], condominium_id=condominium_id
                )
                is not None
            )
        if kind == Unit.Kind.APARTMENT:
            return (
                self._repo.get_by_apartment(
                    normalized["apartment"], condominium_id=condominium_id
                )
                is not None
            )
        return (
            self._repo.get_by_apartment_block(
                normalized["apartment"],
                normalized["block"],
                condominium_id=condominium_id,
            )
            is not None
        )

    def _with_occupancy(self, unit: Unit) -> dict:
        is_occupied = self._memberships.get_active_owner(unit.id) is not None
        return {"unit": unit, "is_occupied": is_occupied}
