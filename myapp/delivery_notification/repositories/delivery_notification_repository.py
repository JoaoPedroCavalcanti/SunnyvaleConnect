"""Dumb repository for DeliveryNotificationModel."""

from abc import ABC, abstractmethod
from typing import Iterable

from delivery_notification.models import DeliveryNotificationModel


class IDeliveryNotificationRepository(ABC):
    @abstractmethod
    def list_all(self) -> Iterable[DeliveryNotificationModel]: ...

    @abstractmethod
    def get_by_id(self, pk: int) -> DeliveryNotificationModel | None: ...

    @abstractmethod
    def create(self, data: dict) -> DeliveryNotificationModel: ...


class DjangoDeliveryNotificationRepository(IDeliveryNotificationRepository):
    def list_all(self):
        return DeliveryNotificationModel.objects.all().order_by("-created_at")

    def get_by_id(self, pk):
        return DeliveryNotificationModel.objects.filter(pk=pk).first()

    def create(self, data):
        return DeliveryNotificationModel.objects.create(**data)
