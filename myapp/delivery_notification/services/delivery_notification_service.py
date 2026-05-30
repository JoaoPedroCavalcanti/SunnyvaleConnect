"""Business rules for delivery notifications."""

from abc import ABC, abstractmethod

from delivery_notification.models import DeliveryNotificationModel
from delivery_notification.repositories.delivery_notification_repository import (
    IDeliveryNotificationRepository,
)
from shared.exceptions import NotFoundError
from shared.infrastructure.email_sender import IEmailSender
from users.repositories.user_repository import IUserRepository


class IDeliveryNotificationService(ABC):
    @abstractmethod
    def list(self): ...

    @abstractmethod
    def get(self, pk: int) -> DeliveryNotificationModel: ...

    @abstractmethod
    def send(self, payload: dict) -> DeliveryNotificationModel: ...


class DeliveryNotificationService(IDeliveryNotificationService):
    def __init__(
        self,
        repository: IDeliveryNotificationRepository,
        user_repository: IUserRepository,
        email_sender: IEmailSender,
    ):
        self._repo = repository
        self._user_repo = user_repository
        self._email = email_sender

    def list(self):
        return self._repo.list_all()

    def get(self, pk):
        instance = self._repo.get_by_id(pk)
        if not instance:
            raise NotFoundError("No delivery notification matches the given query.")
        return instance

    def send(self, payload: dict) -> DeliveryNotificationModel:
        user = self._user_repo.get_by_id(payload["user_to_delivery"].id if hasattr(payload["user_to_delivery"], "id") else payload["user_to_delivery"])
        if not user:
            raise NotFoundError("User to deliver not found.")

        instance = self._repo.create(payload)

        self._email.send_delivery_notification(
            to_email=user.email,
            user_name=user.username,
            delivery_platform=payload.get("delivery_platform"),
            delivery_from=payload.get("delivery_from"),
        )
        return instance
