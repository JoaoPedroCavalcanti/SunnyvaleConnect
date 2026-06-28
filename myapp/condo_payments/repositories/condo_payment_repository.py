"""Dumb repository for CondoPaymentModel."""

from abc import ABC, abstractmethod

from condo_payments.models import CondoPaymentModel


class ICondoPaymentRepository(ABC):
    @abstractmethod
    def list_all(self, *, condominium_id: int): ...

    @abstractmethod
    def list_for_user(self, user_id: int, *, condominium_id: int): ...

    @abstractmethod
    def get_by_id(self, pk: int) -> CondoPaymentModel | None: ...

    @abstractmethod
    def list_by_ids(self, ids: list[int]): ...

    @abstractmethod
    def create(self, data: dict) -> CondoPaymentModel: ...

    @abstractmethod
    def update(self, instance: CondoPaymentModel, data: dict) -> CondoPaymentModel: ...

    @abstractmethod
    def delete(self, instance: CondoPaymentModel) -> None: ...

    @abstractmethod
    def bulk_set_status(self, instances: list[CondoPaymentModel], new_status: str) -> None: ...


class DjangoCondoPaymentRepository(ICondoPaymentRepository):
    def list_all(self, *, condominium_id):
        return (
            CondoPaymentModel.objects.filter(payer_user__condominium_id=condominium_id)
            .order_by("-created_at")
        )

    def list_for_user(self, user_id, *, condominium_id):
        return CondoPaymentModel.objects.filter(
            payer_user_id=user_id,
            payer_user__condominium_id=condominium_id,
        ).order_by("-created_at")

    def get_by_id(self, pk):
        return CondoPaymentModel.objects.filter(pk=pk).first()

    def list_by_ids(self, ids):
        return list(CondoPaymentModel.objects.filter(id__in=ids))

    def create(self, data):
        return CondoPaymentModel.objects.create(**data)

    def update(self, instance, data):
        for k, v in data.items():
            setattr(instance, k, v)
        instance.save()
        return instance

    def delete(self, instance):
        instance.delete()

    def bulk_set_status(self, instances, new_status):
        for inst in instances:
            inst.status = new_status
            inst.save()
