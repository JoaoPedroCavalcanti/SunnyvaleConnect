"""Business rules for condo payments."""

from abc import ABC, abstractmethod

from condo_payments.models import CondoPaymentModel
from condo_payments.repositories.condo_payment_repository import (
    ICondoPaymentRepository,
)
from shared.exceptions import BusinessRuleError, NotFoundError, PermissionDeniedError


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
                "Only staff users can perform this action."
            )

    def list_for(self, user):
        if user.is_staff:
            return self._repo.list_all()
        return self._repo.list_for_user(user.id)

    def get_for(self, user, pk):
        instance = self._repo.get_by_id(pk)
        if not instance:
            raise NotFoundError("No payment matches the given query.")
        if not user.is_staff and instance.payer_user_id != user.id:
            raise NotFoundError("No payment matches the given query.")
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
                "The IDs list is invalid or empty", field="Invalid JSON"
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
                message=str(invalid),
                field="These IDs are invalid or already paid",
            )

        self._repo.bulk_set_status(to_update, "paid")
