"""Business rules for visitor groups (reusable lists of visitors)."""

from abc import ABC, abstractmethod

from shared.exceptions import BusinessRuleError, NotFoundError
from shared.roles import ensure_not_employee, is_admin
from shared.tenant import assert_same_condominium, require_condominium_id
from visitor_access.models import VisitorGroupModel
from visitor_access.repositories.visitor_group_repository import (
    IVisitorGroupRepository,
)
from visitor_access.services.visitor_access_service import IVisitorAccessService


class IVisitorGroupService(ABC):
    @abstractmethod
    def list_for(self, user): ...

    @abstractmethod
    def get_for(self, user, pk: int) -> VisitorGroupModel: ...

    @abstractmethod
    def create(self, user, payload: dict) -> VisitorGroupModel: ...

    @abstractmethod
    def update(self, user, pk: int, payload: dict) -> VisitorGroupModel: ...

    @abstractmethod
    def delete(self, user, pk: int) -> None: ...

    @abstractmethod
    def schedule_visit(self, user, pk: int, payload: dict): ...


class VisitorGroupService(IVisitorGroupService):
    def __init__(
        self,
        repository: IVisitorGroupRepository,
        visitor_access_service: IVisitorAccessService,
    ):
        self._repo = repository
        self._access = visitor_access_service

    # ------------------------------------------------------------------ #
    # listing                                                            #
    # ------------------------------------------------------------------ #
    def list_for(self, user):
        if user.is_staff:
            return self._repo.list_all(
                condominium_id=require_condominium_id(user)
            )
        return self._repo.list_for_user(user.id)

    def get_for(self, user, pk):
        instance = self._repo.get_by_id(pk)
        if not instance:
            raise NotFoundError("Nenhum grupo de visitantes encontrado.")
        assert_same_condominium(user, instance.host_user.condominium_id)
        if not user.is_staff and instance.host_user_id != user.id:
            raise NotFoundError("Nenhum grupo de visitantes encontrado.")
        return instance

    # ------------------------------------------------------------------ #
    # create / update / delete                                           #
    # ------------------------------------------------------------------ #
    def create(self, user, payload: dict):
        ensure_not_employee(user, action="gerenciar grupos de visitantes")
        data = dict(payload)
        members = data.pop("members", []) or []
        name = (data.get("name") or "").strip()

        if not name:
            raise BusinessRuleError("O nome é obrigatório.", field="name")

        self._validate_members(members)

        if self._repo.exists_with_name_for_user(user.id, name):
            raise BusinessRuleError(
                "Você já tem um grupo com esse nome.", field="name"
            )

        group = self._repo.create({"name": name, "host_user": user})
        self._repo.add_members(group, members)
        return self._repo.get_by_id(group.id)

    def update(self, user, pk: int, payload: dict):
        ensure_not_employee(user, action="gerenciar grupos de visitantes")
        instance = self.get_for(user, pk)
        data = dict(payload)

        new_name = data.get("name")
        if new_name is not None:
            new_name = new_name.strip()
            if not new_name:
                raise BusinessRuleError("O nome não pode ficar em branco.", field="name")
            if self._repo.exists_with_name_for_user(
                instance.host_user_id, new_name, exclude_pk=instance.id
            ):
                raise BusinessRuleError(
                    "Você já tem um grupo com esse nome.", field="name"
                )
            self._repo.update(instance, {"name": new_name})

        if "members" in data:
            members = data["members"] or []
            self._validate_members(members)
            self._repo.replace_members(instance, members)

        return self._repo.get_by_id(instance.id)

    def delete(self, user, pk: int) -> None:
        ensure_not_employee(user, action="gerenciar grupos de visitantes")
        instance = self.get_for(user, pk)
        self._repo.delete(instance)

    # ------------------------------------------------------------------ #
    # schedule a visit for the whole group                               #
    # ------------------------------------------------------------------ #
    def schedule_visit(self, user, pk: int, payload: dict):
        ensure_not_employee(user, action="agendar visitas")
        """Create one visit row per group member (each with own QR/code)."""
        group = self.get_for(user, pk)
        if group.members.count() == 0:
            raise BusinessRuleError(
                "Este grupo não tem membros. Adicione membros antes de agendar uma visita."
            )

        scheduled_date = payload.get("scheduled_date")
        if scheduled_date is None:
            raise BusinessRuleError(
                "scheduled_date é obrigatório.", field="scheduled_date"
            )

        host_user = group.host_user
        acting_user = host_user if is_admin(user) else user

        visit_payload = {
            "scheduled_date": scheduled_date,
            "all_day": payload.get("all_day", False),
            "qr_access_enabled": payload.get("qr_access_enabled", False),
            "description": payload.get("description", "") or "",
            "visitor_group": group,
        }
        if not visit_payload["all_day"] and payload.get("checkout_date_time"):
            visit_payload["checkout_date_time"] = payload["checkout_date_time"]

        return self._access.create_group_visits(acting_user, visit_payload)

    # ------------------------------------------------------------------ #
    # helpers                                                            #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _validate_members(members: list[dict]) -> None:
        for idx, m in enumerate(members):
            name = (m.get("name") or "").strip()
            if not name:
                raise BusinessRuleError(
                    f"O membro no índice {idx} precisa de um nome.", field="members"
                )
