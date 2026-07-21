from abc import ABC, abstractmethod

from condominiums.repositories.condominium_repository import (
    ICondominiumRepository,
)
from reservations.models import ReservableLocation
from reservations.repositories.reservable_location_repository import (
    IReservableLocationRepository,
)
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


class IReservableLocationService(ABC):
    @abstractmethod
    def list(self, user, tenant: dict | None = None): ...

    @abstractmethod
    def get(
        self, user, pk: int, tenant: dict | None = None
    ) -> ReservableLocation: ...

    @abstractmethod
    def create(self, user, payload: dict) -> ReservableLocation: ...

    @abstractmethod
    def update(
        self, user, pk: int, payload: dict
    ) -> ReservableLocation: ...

    @abstractmethod
    def archive(self, user, pk: int) -> None: ...


class ReservableLocationService(IReservableLocationService):
    def __init__(
        self,
        repository: IReservableLocationRepository,
        condominium_repository: ICondominiumRepository,
    ):
        self._repo = repository
        self._condominiums = condominium_repository

    def list(self, user, tenant=None):
        condominium_id = self._target_condominium_id(user, tenant)
        return self._repo.list_for_condominium(
            condominium_id, active_only=True
        )

    def get(self, user, pk, tenant=None):
        instance = self._repo.get_by_id(pk)
        if not instance or not instance.is_active:
            raise NotFoundError("Local reservável não encontrado.")
        if is_platform_superuser(user):
            target_id = self._target_condominium_id(user, tenant)
            if instance.condominium_id != target_id:
                raise NotFoundError("Local reservável não encontrado.")
        else:
            assert_same_condominium(user, instance.condominium_id)
        return instance

    def create(self, user, payload):
        self._ensure_platform_superuser(user)
        data = dict(payload)
        condominium = self._resolve_condominium(data)
        name = (data.get("name") or "").strip()
        if self._repo.exists_with_name(condominium.id, name):
            raise BusinessRuleError(
                "Já existe um local reservável com esse nome.",
                field="name",
            )
        data["name"] = name
        data["icon"] = (data.get("icon") or "").strip()
        data["condominium"] = condominium
        data.pop("condominium_id", None)
        data.pop("condominium_code", None)
        return self._repo.create(data)

    def update(self, user, pk, payload):
        self._ensure_platform_superuser(user)
        instance = self._repo.get_by_id(pk)
        if not instance:
            raise NotFoundError("Local reservável não encontrado.")
        data = dict(payload)
        if "name" in data:
            name = (data["name"] or "").strip()
            if self._repo.exists_with_name(
                instance.condominium_id,
                name,
                exclude_id=instance.id,
            ):
                raise BusinessRuleError(
                    "Já existe um local reservável com esse nome.",
                    field="name",
                )
            data["name"] = name
        if "icon" in data:
            data["icon"] = (data["icon"] or "").strip()
        return self._repo.update(instance, data)

    def archive(self, user, pk):
        self._ensure_platform_superuser(user)
        instance = self._repo.get_by_id(pk)
        if not instance:
            raise NotFoundError("Local reservável não encontrado.")
        self._repo.update(instance, {"is_active": False})

    @staticmethod
    def _ensure_platform_superuser(user):
        if not is_platform_superuser(user):
            raise PermissionDeniedError(
                "Apenas superusuários da plataforma podem gerenciar locais reserváveis."
            )

    def _target_condominium_id(self, user, tenant):
        if not is_platform_superuser(user):
            return require_condominium_id(user)
        return self._resolve_condominium(dict(tenant or {})).id

    def _resolve_condominium(self, data):
        condominium_id = data.get("condominium_id")
        condominium_code = (data.get("condominium_code") or "").strip()
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
            raise NotFoundError("Condomínio não encontrado.")
        return condominium
