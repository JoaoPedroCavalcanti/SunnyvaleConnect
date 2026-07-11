"""Business rules for delivery notifications."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from delivery_notification.models import DeliveryNotificationModel
from delivery_notification.repositories.delivery_notification_repository import (
    IDeliveryNotificationRepository,
)
from units.models import Unit, UnitMembership
from units.repositories.unit_membership_repository import IUnitMembershipRepository
from units.repositories.unit_repository import IUnitRepository
from shared.exceptions import BusinessRuleError, NotFoundError, PermissionDeniedError
from shared.infrastructure.email_sender import IEmailSender
from shared.roles import can_doorman_ops
from shared.tenant import assert_same_condominium, require_condominium_id


@dataclass(frozen=True)
class DeliveryUnitItem:
    id: int
    display_name: str
    holder_name: str
    status: str


class IDeliveryNotificationService(ABC):
    @abstractmethod
    def list_apartments(self, user) -> list[DeliveryUnitItem]: ...

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
        unit_repository: IUnitRepository,
        membership_repository: IUnitMembershipRepository,
        email_sender: IEmailSender,
    ):
        self._repo = repository
        self._units = unit_repository
        self._memberships = membership_repository
        self._email = email_sender

    def list_apartments(self, user) -> list[DeliveryUnitItem]:
        if not can_doorman_ops(user):
            raise PermissionDeniedError(
                "Only admins or doorman staff can list delivery apartments."
            )

        units = [
            u
            for u in self._units.list_all(
                condominium_id=require_condominium_id(user)
            )
            if u.status != Unit.Status.ARCHIVED
        ]
        if not units:
            return []

        unit_ids = [u.id for u in units]
        owners = self._memberships.list_active_for_units(unit_ids)
        owner_by_unit = {
            m.unit_id: m
            for m in owners
            if m.role == UnitMembership.Role.OWNER
        }

        items: list[DeliveryUnitItem] = []
        for unit in units:
            owner_membership = owner_by_unit.get(unit.id)
            holder_name = ""
            if owner_membership and owner_membership.user:
                owner_user = owner_membership.user
                holder_name = owner_user.full_name or owner_user.username
            items.append(
                DeliveryUnitItem(
                    id=unit.id,
                    display_name=unit.display_name(),
                    holder_name=holder_name,
                    status=unit.status,
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
        assert_same_condominium(user, instance.unit.condominium_id)
        return instance

    def send(self, user, payload: dict) -> DeliveryNotificationModel:
        unit_id = payload["unit_id"]
        unit = self._units.get_by_id(unit_id)
        if not unit:
            raise NotFoundError("No unit matches the given unit_id.")
        assert_same_condominium(user, unit.condominium_id)
        if unit.status != Unit.Status.ACTIVE:
            raise BusinessRuleError(
                "This unit is not active; cannot register a delivery.",
                field="unit_id",
            )

        owner_membership = self._memberships.get_active_owner(unit.id)
        if not owner_membership:
            raise BusinessRuleError(
                "This unit has no active owner; cannot notify delivery.",
                field="unit_id",
            )

        extra_owners = list(self._memberships.list_active_owners(unit.id))
        if len(extra_owners) > 1:
            raise BusinessRuleError(
                "This unit has more than one active owner.",
                field="unit_id",
            )

        owner = owner_membership.user
        if not owner.email:
            raise BusinessRuleError(
                "The unit owner has no email registered; cannot notify delivery.",
                field="unit_id",
            )

        create_data = {
            key: value
            for key, value in payload.items()
            if key != "unit_id"
        }
        create_data["unit"] = unit
        create_data["notified_holder_name"] = owner.full_name or owner.username
        create_data["notified_holder_email"] = owner.email
        instance = self._repo.create(create_data)

        self._email.send_delivery_notification(
            to_email=owner.email,
            user_name=owner.full_name or owner.username,
            delivery_platform=payload.get("delivery_platform"),
            delivery_from=payload.get("delivery_from"),
            apartment=unit.apartment,
            block=unit.block,
        )
        return instance
