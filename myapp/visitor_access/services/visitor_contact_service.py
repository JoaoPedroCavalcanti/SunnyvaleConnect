"""Business rules for reusable solo visitor contacts."""

from abc import ABC, abstractmethod

from shared.exceptions import BusinessRuleError, NotFoundError
from shared.roles import ensure_not_employee, is_admin
from shared.tenant import assert_same_condominium, require_condominium_id
from visitor_access.models import VisitorContactModel
from visitor_access.repositories.visitor_contact_repository import (
    IVisitorContactRepository,
)
from visitor_access.services.visitor_access_service import IVisitorAccessService


class IVisitorContactService(ABC):
    @abstractmethod
    def list_for(self, user): ...

    @abstractmethod
    def get_for(self, user, pk: int) -> VisitorContactModel: ...

    @abstractmethod
    def create(self, user, payload: dict) -> VisitorContactModel: ...

    @abstractmethod
    def update(self, user, pk: int, payload: dict) -> VisitorContactModel: ...

    @abstractmethod
    def delete(self, user, pk: int) -> None: ...

    @abstractmethod
    def schedule_visit(self, user, pk: int, payload: dict): ...


class VisitorContactService(IVisitorContactService):
    def __init__(
        self,
        repository: IVisitorContactRepository,
        visitor_access_service: IVisitorAccessService,
    ):
        self._repo = repository
        self._access = visitor_access_service

    def list_for(self, user):
        if user.is_staff:
            return self._repo.list_all(
                condominium_id=require_condominium_id(user)
            )
        return self._repo.list_for_user(user.id)

    def get_for(self, user, pk):
        instance = self._repo.get_by_id(pk)
        if not instance:
            raise NotFoundError("Nenhum contato de visitante encontrado.")
        assert_same_condominium(user, instance.host_user.condominium_id)
        if not user.is_staff and instance.host_user_id != user.id:
            raise NotFoundError("Nenhum contato de visitante encontrado.")
        return instance

    def create(self, user, payload: dict):
        ensure_not_employee(user, action="gerenciar contatos de visitantes")
        name = (payload.get("name") or "").strip()
        if not name:
            raise BusinessRuleError("O nome é obrigatório.", field="name")

        if self._repo.exists_with_name_for_user(user.id, name):
            raise BusinessRuleError(
                "Você já tem um contato com esse nome.",
                field="name",
            )

        email = (payload.get("email") or "").strip()
        return self._repo.create(
            {"name": name, "email": email, "host_user": user}
        )

    def update(self, user, pk: int, payload: dict):
        ensure_not_employee(user, action="gerenciar contatos de visitantes")
        instance = self.get_for(user, pk)
        data = {}

        if "name" in payload:
            name = (payload.get("name") or "").strip()
            if not name:
                raise BusinessRuleError("O nome não pode ficar em branco.", field="name")
            if self._repo.exists_with_name_for_user(
                instance.host_user_id, name, exclude_pk=instance.id
            ):
                raise BusinessRuleError(
                    "Você já tem um contato com esse nome.",
                    field="name",
                )
            data["name"] = name

        if "email" in payload:
            data["email"] = (payload.get("email") or "").strip()

        if not data:
            return instance
        return self._repo.update(instance, data)

    def delete(self, user, pk: int) -> None:
        ensure_not_employee(user, action="gerenciar contatos de visitantes")
        instance = self.get_for(user, pk)
        self._repo.delete(instance)

    def schedule_visit(self, user, pk: int, payload: dict):
        ensure_not_employee(user, action="agendar visitas")
        contact = self.get_for(user, pk)
        scheduled_date = payload.get("scheduled_date")
        if scheduled_date is None:
            raise BusinessRuleError(
                "scheduled_date é obrigatório.", field="scheduled_date"
            )

        host_user = contact.host_user
        acting_user = host_user if is_admin(user) else user

        visit_payload = {
            "visitor_name": contact.name,
            "email": contact.email or "",
            "scheduled_date": scheduled_date,
            "all_day": payload.get("all_day", False),
            "qr_access_enabled": payload.get("qr_access_enabled", False),
            "description": payload.get("description", "") or "",
            "host_user": host_user,
        }
        if not visit_payload["all_day"] and payload.get("checkout_date_time"):
            visit_payload["checkout_date_time"] = payload["checkout_date_time"]

        return self._access.create(acting_user, visit_payload)
