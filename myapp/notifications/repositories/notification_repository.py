"""Dumb repository for NotificationModel."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Iterable

from notifications.models import NotificationModel


class INotificationRepository(ABC):
    @abstractmethod
    def list_for_user(
        self, user_id: int, *, unread_only: bool = False
    ) -> Iterable[NotificationModel]: ...

    @abstractmethod
    def count_unread(self, user_id: int) -> int: ...

    @abstractmethod
    def get_by_id(self, pk: int) -> NotificationModel | None: ...

    @abstractmethod
    def create(self, data: dict) -> NotificationModel: ...

    @abstractmethod
    def mark_read(
        self, instance: NotificationModel, *, read_at: datetime
    ) -> NotificationModel: ...

    @abstractmethod
    def mark_all_read(self, user_id: int, *, read_at: datetime) -> int: ...


class DjangoNotificationRepository(INotificationRepository):
    def list_for_user(self, user_id, *, unread_only=False):
        qs = NotificationModel.objects.filter(recipient_id=user_id).order_by(
            "-created_at"
        )
        if unread_only:
            qs = qs.filter(read_at__isnull=True)
        return qs

    def count_unread(self, user_id):
        return NotificationModel.objects.filter(
            recipient_id=user_id, read_at__isnull=True
        ).count()

    def get_by_id(self, pk):
        return NotificationModel.objects.filter(pk=pk).first()

    def create(self, data):
        return NotificationModel.objects.create(**data)

    def mark_read(self, instance, *, read_at):
        instance.read_at = read_at
        instance.save(update_fields=["read_at"])
        return instance

    def mark_all_read(self, user_id, *, read_at):
        return NotificationModel.objects.filter(
            recipient_id=user_id, read_at__isnull=True
        ).update(read_at=read_at)
