"""Business rules for delivery notifications."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from delivery_notification.models import DeliveryNotificationModel
from delivery_notification.repositories.delivery_notification_repository import (
    IDeliveryNotificationRepository,
)
from households.models import Household
from households.repositories.household_repository import IHouseholdRepository
from households.repositories.membership_repository import IMembershipRepository
from shared.exceptions import BusinessRuleError, NotFoundError, PermissionDeniedError
from shared.infrastructure.email_sender import IEmailSender
from shared.roles import can_doorman_ops
from shared.tenant import assert_same_condominium, require_condominium_id


@dataclass(frozen=True)
class DeliveryApartmentItem:
    id: int
    apartment: str
    block: str
    holder_name: str
    status: str


class IDeliveryNotificationService(ABC):
    @abstractmethod
    def list_apartments(self, user) -> list[DeliveryApartmentItem]: ...

    @abstractmethod
    def list(self, user): ...

    @abstractmethod
    def get(self, user, pk: int) -> DeliveryNotificationModel: ...

    @abstractmethod
    def send(self, user, payload: dict) -> DeliveryNotificationModel: ...


class DeliveryNotificationService(IDeliveryNotificationService):
    def __init__(
        self,
        repository: IDeliveryNotificationRepository,
        household_repository: IHouseholdRepository,
        membership_repository: IMembershipRepository,
        email_sender: IEmailSender,
    ):
        self._repo = repository
        self._households = household_repository
        self._memberships = membership_repository
        self._email = email_sender

    def list_apartments(self, user) -> list[DeliveryApartmentItem]:
        if not can_doorman_ops(user):
            raise PermissionDeniedError(
                "Only admins or doorman staff can list delivery apartments."
            )

        households = [
            h
            for h in self._households.list_all(
                condominium_id=require_condominium_id(user)
            )
            if h.status != Household.Status.ARCHIVED
        ]
        if not households:
            return []

        household_ids = [h.id for h in households]
        holders = self._memberships.list_active_holders_for_households(
            household_ids
        )
        holder_by_household = {m.household_id: m for m in holders}

        items: list[DeliveryApartmentItem] = []
        for household in households:
            holder_membership = holder_by_household.get(household.id)
            holder_name = ""
            if holder_membership and holder_membership.user:
                user = holder_membership.user
                holder_name = user.full_name or user.username
            items.append(
                DeliveryApartmentItem(
                    id=household.id,
                    apartment=household.apartment,
                    block=household.block,
                    holder_name=holder_name,
                    status=household.status,
                )
            )
        return items

    def list(self, user):
        return self._repo.list_all(
            condominium_id=require_condominium_id(user)
        )

    def get(self, user, pk):
        instance = self._repo.get_by_id(pk)
        if not instance:
            raise NotFoundError("No delivery notification matches the given query.")
        assert_same_condominium(user, instance.household.condominium_id)
        return instance

    def send(self, user, payload: dict) -> DeliveryNotificationModel:
        apartment = payload["apartment"]
        block = payload.get("block") or ""

        household = self._households.get_by_apartment_block(
            apartment,
            block,
            condominium_id=require_condominium_id(user),
        )
        if not household:
            raise NotFoundError("No household matches the given apartment and block.")
        if household.status != Household.Status.ACTIVE:
            raise BusinessRuleError(
                "This household is not active; cannot register a delivery.",
                field="apartment",
            )

        holder_membership = self._memberships.get_active_holder(household.id)
        if not holder_membership:
            raise BusinessRuleError(
                "This household has no active holder; cannot notify delivery.",
                field="apartment",
            )

        extra_holders = list(self._memberships.list_active_holders(household.id))
        if len(extra_holders) > 1:
            raise BusinessRuleError(
                "This household has more than one active holder.",
                field="apartment",
            )

        holder = holder_membership.user
        if not holder.email:
            raise BusinessRuleError(
                "The household holder has no email registered; cannot notify delivery.",
                field="apartment",
            )

        create_data = {
            key: value
            for key, value in payload.items()
            if key not in {"apartment", "block"}
        }
        create_data["household"] = household
        create_data["notified_holder_name"] = holder.full_name or holder.username
        create_data["notified_holder_email"] = holder.email
        instance = self._repo.create(create_data)

        self._email.send_delivery_notification(
            to_email=holder.email,
            user_name=holder.full_name or holder.username,
            delivery_platform=payload.get("delivery_platform"),
            delivery_from=payload.get("delivery_from"),
            apartment=household.apartment,
            block=household.block,
        )
        return instance
