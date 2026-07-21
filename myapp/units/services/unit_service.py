"""Business rules for Unit lifecycle (create / list / peek / bulk)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from condominiums.repositories.condominium_repository import ICondominiumRepository
from units.models import Unit
from units.repositories.unit_membership_repository import IUnitMembershipRepository
from units.repositories.unit_repository import IUnitRepository
from shared.exceptions import (
    BusinessRuleError,
    NotFoundError,
    PermissionDeniedError,
)
from shared.tenant import (
    assert_same_condominium,
    is_platform_superuser,
    require_condominium_id,
)
from units.unit_catalog import build_catalog, build_filter_options


def _norm_code(value: str) -> str:
    """Apartment / block codes: trim + uppercase."""
    return (value or "").strip().upper()


def _display_name(value: str) -> str:
    """Named units: preserve casing, only trim."""
    return (value or "").strip()


def _name_key(value: str) -> str:
    """Case-insensitive key for named-unit uniqueness checks."""
    return (value or "").strip().casefold()


@dataclass(frozen=True)
class BulkProvisionResult:
    condominium_id: int
    condominium_code: str
    created_count: int
    skipped_count: int
    created: list


class IUnitService(ABC):
    @abstractmethod
    def list_public(
        self,
        condominium_code: str,
        *,
        block: str | None = None,
        floor: str | None = None,
        apartment: str | None = None,
        name: str | None = None,
    ) -> dict: ...

    @abstractmethod
    def list_public_filters(self, condominium_code: str) -> dict: ...

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
    def bulk_provision(self, user, payload: dict) -> BulkProvisionResult: ...

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

    def list_public(
        self,
        condominium_code: str,
        *,
        block: str | None = None,
        floor: str | None = None,
        apartment: str | None = None,
        name: str | None = None,
    ) -> dict:
        condominium = self._require_active_condominium(condominium_code)
        units = list(
            self._repo.list_all(
                status=Unit.Status.ACTIVE, condominium_id=condominium.id
            )
        )
        entries = [self._with_occupancy(u) for u in units]
        return build_catalog(
            entries,
            condominium_id=condominium.id,
            condominium_code=getattr(condominium, "code", "") or "",
            block=(block or "").strip() or None,
            floor=(floor or "").strip() or None,
            apartment=(apartment or "").strip() or None,
            name=(name or "").strip() or None,
        )

    def list_public_filters(self, condominium_code: str) -> dict:
        condominium = self._require_active_condominium(condominium_code)
        units = list(
            self._repo.list_all(
                status=Unit.Status.ACTIVE, condominium_id=condominium.id
            )
        )
        entries = [self._with_occupancy(u) for u in units]
        return build_filter_options(
            entries,
            condominium_id=condominium.id,
            condominium_code=getattr(condominium, "code", "") or "",
        )

    def _require_active_condominium(self, condominium_code: str):
        condominium = self._condominiums.get_by_code(condominium_code)
        if not condominium or not condominium.is_active:
            raise NotFoundError("Código de condomínio inválido ou inativo.")
        return condominium

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
            raise NotFoundError("Nenhuma unidade encontrada.")
        assert_same_condominium(user, instance.condominium_id)
        if getattr(user, "is_staff", False):
            return instance
        if not self._memberships.get_for_user_and_unit(user.id, instance.id):
            raise NotFoundError("Nenhuma unidade encontrada.")
        return instance

    def peek(self, pk, *, condominium_id: int):
        instance = self._repo.get_by_id(pk)
        if not instance or instance.condominium_id != condominium_id:
            return None
        return instance

    def create(self, admin, payload: dict) -> Unit:
        if not getattr(admin, "is_staff", False):
            raise PermissionDeniedError("Apenas administradores podem criar unidades.")

        condominium_id = require_condominium_id(admin)
        normalized = self.validate_kind_fields(payload)

        if self._duplicate_exists(condominium_id, normalized):
            raise BusinessRuleError(
                "Já existe uma unidade com esses identificadores.",
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

    def bulk_provision(self, user, payload: dict) -> BulkProvisionResult:
        """Expand block/floor recipes into units. Platform superuser only."""
        if not is_platform_superuser(user):
            raise PermissionDeniedError(
                "Apenas superusuários da plataforma podem provisionar unidades em massa."
            )

        condominium = self._resolve_condominium(payload)
        skip_existing = payload.get("skip_existing", True)
        candidates = self._expand_bulk_candidates(payload)

        existing = list(self._repo.list_all(condominium_id=condominium.id))
        existing_block = {
            (_norm_code(u.apartment), _norm_code(u.block))
            for u in existing
            if u.kind == Unit.Kind.APARTMENT_BLOCK
        }
        existing_named = {
            _name_key(u.name) for u in existing if u.kind == Unit.Kind.NAMED
        }
        existing_apt = {
            _norm_code(u.apartment)
            for u in existing
            if u.kind == Unit.Kind.APARTMENT
        }

        to_create: list[dict] = []
        skipped = 0
        for item in candidates:
            kind = item["kind"]
            if kind == Unit.Kind.APARTMENT_BLOCK:
                key = (_norm_code(item["apartment"]), _norm_code(item["block"]))
                is_dup = key in existing_block
            elif kind == Unit.Kind.NAMED:
                is_dup = _name_key(item["name"]) in existing_named
            else:
                is_dup = _norm_code(item["apartment"]) in existing_apt

            if is_dup:
                if skip_existing:
                    skipped += 1
                    continue
                raise BusinessRuleError(
                    "Já existe uma unidade com esses identificadores.",
                    field="blocks",
                )

            row = {
                "kind": kind,
                "name": _display_name(item.get("name", "")),
                "apartment": _norm_code(item.get("apartment", "")),
                "block": _norm_code(item.get("block", "")),
                "status": Unit.Status.ACTIVE,
                "condominium_id": condominium.id,
            }
            to_create.append(row)
            if kind == Unit.Kind.APARTMENT_BLOCK:
                existing_block.add((row["apartment"], row["block"]))
            elif kind == Unit.Kind.NAMED:
                existing_named.add(_name_key(row["name"]))
            else:
                existing_apt.add(row["apartment"])

        created = self._repo.bulk_create(to_create) if to_create else []
        return BulkProvisionResult(
            condominium_id=condominium.id,
            condominium_code=getattr(condominium, "code", "") or "",
            created_count=len(created),
            skipped_count=skipped,
            created=list(created),
        )

    def _resolve_condominium(self, payload: dict):
        condominium_id = payload.get("condominium_id")
        condominium_code = (payload.get("condominium_code") or "").strip()
        if condominium_id is not None and condominium_code:
            raise BusinessRuleError(
                "Informe apenas condominium_id ou condominium_code, não os dois.",
                field="condominium_id",
            )
        if condominium_id is not None:
            condominium = self._condominiums.get_by_id(condominium_id)
        elif condominium_code:
            condominium = self._condominiums.get_by_code(condominium_code)
        else:
            raise BusinessRuleError(
                "condominium_id ou condominium_code é obrigatório.",
                field="condominium_code",
            )
        if not condominium or not getattr(condominium, "is_active", True):
            raise NotFoundError("Condomínio inválido ou inativo.")
        return condominium

    def _expand_bulk_candidates(self, payload: dict) -> list[dict]:
        blocks = payload.get("blocks") or []
        towers = payload.get("towers") or []
        named_units = payload.get("named_units") or []
        apartments = payload.get("apartments") or []
        number_range = payload.get("number_range")
        if (
            not blocks
            and not towers
            and not named_units
            and not apartments
            and not number_range
        ):
            raise BusinessRuleError(
                "Informe ao menos um de blocks, towers, number_range, "
                "apartments ou named_units.",
                field="blocks",
            )

        candidates: list[dict] = []

        for block_spec in blocks:
            block = (block_spec.get("block") or "").strip()
            if not block:
                raise BusinessRuleError("block é obrigatório.", field="blocks")
            candidates.extend(
                self._expand_floor_grid(
                    floors=block_spec.get("floors"),
                    units=block_spec.get("units") or [],
                    kind=Unit.Kind.APARTMENT_BLOCK,
                    block=block,
                    field="blocks",
                )
            )

        for tower_spec in towers:
            candidates.extend(
                self._expand_floor_grid(
                    floors=tower_spec.get("floors"),
                    units=tower_spec.get("units") or [],
                    kind=Unit.Kind.APARTMENT,
                    block="",
                    field="towers",
                )
            )

        if number_range:
            candidates.extend(self._expand_number_range(number_range))

        for apt in apartments:
            apartment = str(apt).strip()
            if not apartment:
                raise BusinessRuleError(
                    "apartments não pode conter valores vazios.",
                    field="apartments",
                )
            candidates.append(
                {
                    "kind": Unit.Kind.APARTMENT,
                    "apartment": apartment,
                    "block": "",
                    "name": "",
                }
            )

        for name in named_units:
            cleaned = str(name).strip()
            if not cleaned:
                raise BusinessRuleError(
                    "named_units não pode conter valores vazios.",
                    field="named_units",
                )
            candidates.append(
                {
                    "kind": Unit.Kind.NAMED,
                    "name": cleaned,
                    "apartment": "",
                    "block": "",
                }
            )

        return candidates

    def _expand_floor_grid(
        self,
        *,
        floors,
        units: list,
        kind: str,
        block: str,
        field: str,
    ) -> list[dict]:
        if not isinstance(floors, int) or floors < 1:
            raise BusinessRuleError(
                "floors deve ser um número inteiro positivo.", field=field
            )
        if floors > 100:
            raise BusinessRuleError("floors não pode exceder 100.", field=field)
        if not units:
            raise BusinessRuleError(
                "units (por andar) é obrigatório.", field=field
            )
        cleaned_units: list[str] = []
        for unit_suffix in units:
            suffix = str(unit_suffix).strip()
            if not suffix:
                raise BusinessRuleError(
                    "os sufixos de unidade não podem ser vazios.", field=field
                )
            cleaned_units.append(suffix)

        out: list[dict] = []
        for floor in range(1, floors + 1):
            for suffix in cleaned_units:
                out.append(
                    {
                        "kind": kind,
                        "apartment": f"{floor}{suffix}",
                        "block": block,
                        "name": "",
                    }
                )
        return out

    def _expand_number_range(self, spec: dict) -> list[dict]:
        start = spec.get("start")
        end = spec.get("end")
        pad = spec.get("pad", 0)
        as_named = bool(spec.get("as_named", False))
        name_prefix = spec.get("name_prefix", "Casa ")
        if not isinstance(start, int) or not isinstance(end, int):
            raise BusinessRuleError(
                "number_range.start/end devem ser inteiros.",
                field="number_range",
            )
        if end < start:
            raise BusinessRuleError(
                "number_range.end deve ser >= start.",
                field="number_range",
            )
        if end - start + 1 > 5000:
            raise BusinessRuleError(
                "number_range não pode exceder 5000 unidades.",
                field="number_range",
            )

        out: list[dict] = []
        for n in range(start, end + 1):
            label = str(n).zfill(pad) if pad else str(n)
            if as_named:
                out.append(
                    {
                        "kind": Unit.Kind.NAMED,
                        "name": f"{name_prefix}{label}".strip(),
                        "apartment": "",
                        "block": "",
                    }
                )
            else:
                out.append(
                    {
                        "kind": Unit.Kind.APARTMENT,
                        "apartment": label,
                        "block": "",
                        "name": "",
                    }
                )
        return out

    def validate_kind_fields(self, payload: dict) -> dict:
        kind = payload.get("kind")
        if kind not in Unit.Kind.values:
            raise BusinessRuleError("Tipo de unidade inválido.", field="kind")

        name = _display_name(payload.get("name") or "")
        apartment = _norm_code(payload.get("apartment") or "")
        block = _norm_code(payload.get("block") or "")

        if kind == Unit.Kind.NAMED:
            if not name:
                raise BusinessRuleError("name é obrigatório.", field="name")
            if apartment or block:
                raise BusinessRuleError(
                    "apartment e block devem ficar vazios para unidades NAMED.",
                    field="apartment",
                )
            return {"kind": kind, "name": name, "apartment": "", "block": ""}

        if kind == Unit.Kind.APARTMENT:
            if not apartment:
                raise BusinessRuleError(
                    "apartment é obrigatório.", field="apartment"
                )
            if name or block:
                raise BusinessRuleError(
                    "name e block devem ficar vazios para unidades APARTMENT.",
                    field="name",
                )
            return {
                "kind": kind,
                "name": "",
                "apartment": apartment,
                "block": "",
            }

        if not apartment:
            raise BusinessRuleError("apartment é obrigatório.", field="apartment")
        if not block:
            raise BusinessRuleError("block é obrigatório.", field="block")
        if name:
            raise BusinessRuleError(
                "name deve ficar vazio para unidades APARTMENT_BLOCK.", field="name"
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
