"""Dumb repository for DeliveryNotificationModel."""

from abc import ABC, abstractmethod
from typing import Iterable

from delivery_notification.models import DeliveryNotificationModel


class IDeliveryNotificationRepository(ABC):
    @abstractmethod
    def list_all(self, *, condominium_id: int) -> Iterable[DeliveryNotificationModel]: ...

    @abstractmethod
    def get_by_id(self, pk: int) -> DeliveryNotificationModel | None: ...

    @abstractmethod
    def create(self, data: dict) -> DeliveryNotificationModel: ...

    @abstractmethod
    def count_created_between(self, start, end, *, condominium_id: int) -> int: ...


class DjangoDeliveryNotificationRepository(IDeliveryNotificationRepository):
    def list_all(self, *, condominium_id):
        return (
            DeliveryNotificationModel.objects.select_related("household")
            .filter(household__condominium_id=condominium_id)
            .order_by("-created_at")
        )

    def get_by_id(self, pk):
        return (
            DeliveryNotificationModel.objects.select_related("household")
            .filter(pk=pk)
            .first()
        )

    def create(self, data):
        return DeliveryNotificationModel.objects.create(**data)

    def count_created_between(self, start, end, *, condominium_id):
        return DeliveryNotificationModel.objects.filter(
            household__condominium_id=condominium_id,
            created_at__gte=start,
            created_at__lt=end,
        ).count()
