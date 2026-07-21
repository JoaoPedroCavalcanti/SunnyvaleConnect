"""Business rules for condo payments."""

from abc import ABC, abstractmethod

from condo_payments.models import CondoPaymentModel
from condo_payments.repositories.condo_payment_repository import (
    ICondoPaymentRepository,
)
from shared.exceptions import BusinessRuleError, NotFoundError, PermissionDeniedError
from shared.tenant import assert_same_condominium, require_condominium_id


class ICondoPaymentService(ABC):
    @abstractmethod
    def list_for(self, user) -> list: ...

    @abstractmethod
    def get_for(self, user, pk: int) -> CondoPaymentModel: ...

    @abstractmethod
    def create(self, user, payload: dict) -> CondoPaymentModel: ...

    @abstractmethod
    def update(self, user, pk: int, payload: dict) -> CondoPaymentModel: ...

    @abstractmethod
    def delete(self, user, pk: int) -> None: ...

    @abstractmethod
    def mark_as_paid(self, user, payment_ids: list[int]) -> None: ...


class CondoPaymentService(ICondoPaymentService):
    def __init__(self, repository: ICondoPaymentRepository):
        self._repo = repository

    @staticmethod
    def _require_admin(user) -> None:
        if not getattr(user, "is_staff", False):
            raise PermissionDeniedError(
                "Apenas administradores podem executar esta ação."
            )

    def list_for(self, user):
        condominium_id = require_condominium_id(user)
        if user.is_staff:
            return self._repo.list_all(condominium_id=condominium_id)
        return self._repo.list_for_user(user.id, condominium_id=condominium_id)

    def get_for(self, user, pk):
        instance = self._repo.get_by_id(pk)
        if not instance:
            raise NotFoundError("Nenhum pagamento encontrado.")
        assert_same_condominium(user, instance.payer_user.condominium_id)
        if not user.is_staff and instance.payer_user_id != user.id:
            raise NotFoundError("Nenhum pagamento encontrado.")
        return instance

    def create(self, user, payload):
        self._require_admin(user)
        return self._repo.create(payload)

    def update(self, user, pk, payload):
        self._require_admin(user)
        instance = self.get_for(user, pk)
        return self._repo.update(instance, payload)

    def delete(self, user, pk):
        self._require_admin(user)
        instance = self.get_for(user, pk)
        self._repo.delete(instance)

    def mark_as_paid(self, user, payment_ids):
        self._require_admin(user)
        if not isinstance(payment_ids, list) or len(payment_ids) <= 0:
            raise BusinessRuleError(
                "A lista de IDs é inválida ou está vazia.",
                field="payment_ids",
            )

        found = {p.id: p for p in self._repo.list_by_ids(payment_ids)}
        to_update: list[CondoPaymentModel] = []
        invalid: list[int] = []
        for pid in payment_ids:
            payment = found.get(pid)
            if not payment or payment.status == "paid":
                invalid.append(pid)
            else:
                to_update.append(payment)

        if invalid:
            raise BusinessRuleError(
                message=(
                    "Estes IDs são inválidos ou já estão pagos: "
                    f"{invalid}."
                ),
                field="payment_ids",
            )

        self._repo.bulk_set_status(to_update, "paid")
