"""Business rules for in-app notifications."""

from abc import ABC, abstractmethod

from django.utils import timezone

from notifications.models import NotificationModel
from notifications.repositories.notification_repository import (
    INotificationRepository,
)
from shared.exceptions import BusinessRuleError, NotFoundError
from shared.tenant import require_condominium_id


_VALID_TYPES = {choice for choice, _ in NotificationModel.Type.choices}


class INotificationService(ABC):
    @abstractmethod
    def notify(
        self,
        recipient,
        *,
        type: str,
        title: str,
        body: str = "",
        data: dict | None = None,
    ) -> NotificationModel: ...

    @abstractmethod
    def list_for(self, user, *, unread_only: bool = False): ...

    @abstractmethod
    def mark_read(self, user, pk: int) -> NotificationModel: ...

    @abstractmethod
    def mark_all_read(self, user) -> int: ...

    @abstractmethod
    def unread_count(self, user) -> int: ...


class NotificationService(INotificationService):
    def __init__(self, repository: INotificationRepository):
        self._repo = repository

    def notify(self, recipient, *, type, title, body="", data=None):
        notif_type = (type or "").strip()
        if notif_type not in _VALID_TYPES:
            raise BusinessRuleError(
                f"Invalid notification type: {type!r}.",
                field="type",
            )

        title = (title or "").strip()
        if not title:
            raise BusinessRuleError("Title is required.", field="title")

        condominium_id = getattr(recipient, "condominium_id", None)
        if condominium_id is None:
            raise BusinessRuleError(
                "Recipient is not linked to a condominium.",
                field="recipient",
            )

        return self._repo.create(
            {
                "recipient": recipient,
                "condominium_id": condominium_id,
                "type": notif_type,
                "title": title,
                "body": body or "",
                "data": data or {},
            }
        )

    def list_for(self, user, *, unread_only=False):
        require_condominium_id(user)
        return self._repo.list_for_user(user.id, unread_only=unread_only)

    def _get_own(self, user, pk: int) -> NotificationModel:
        instance = self._repo.get_by_id(pk)
        if not instance or instance.recipient_id != user.id:
            raise NotFoundError("No notification matches the given query.")
        return instance

    def mark_read(self, user, pk: int):
        require_condominium_id(user)
        instance = self._get_own(user, pk)
        if instance.read_at is not None:
            return instance
        return self._repo.mark_read(instance, read_at=timezone.now())

    def mark_all_read(self, user) -> int:
        require_condominium_id(user)
        return self._repo.mark_all_read(user.id, read_at=timezone.now())

    def unread_count(self, user) -> int:
        require_condominium_id(user)
        return self._repo.count_unread(user.id)
