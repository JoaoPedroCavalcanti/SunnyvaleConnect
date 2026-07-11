"""Business rules for Hall reservations.

Mirrors ``BBQReservationService``: ownership is per unit (apartment).
Same-day bookings of this resource must not overlap and must leave at
least 30 minutes between one ending and the next starting.
"""

from abc import ABC, abstractmethod
from datetime import date, time

from hall_reservations.models import HallReservationModel
from hall_reservations.repositories.hall_repository import IHallRepository
from units.models import UnitMembership
from units.repositories.unit_membership_repository import IUnitMembershipRepository
from shared.exceptions import (
    BusinessRuleError,
    NotFoundError,
    PermissionDeniedError,
)
from shared.infrastructure.email_sender import IEmailSender
from shared.roles import ensure_not_employee
from shared.tenant import assert_same_condominium, require_condominium_id
from shared.time_slots import slots_overlap, slots_too_close


class IHallReservationService(ABC):
    @abstractmethod
    def list(self, user, status: str | None = None): ...

    @abstractmethod
    def get(self, user, pk: int) -> HallReservationModel: ...

    @abstractmethod
    def create(self, user, payload: dict) -> HallReservationModel: ...

    @abstractmethod
    def update(self, user, pk: int, payload: dict) -> HallReservationModel: ...

    @abstractmethod
    def delete(self, user, pk: int) -> None: ...

    @abstractmethod
    def approve(self, user, pk: int) -> HallReservationModel: ...

    @abstractmethod
    def reject(self, user, pk: int, reason: str = "") -> HallReservationModel: ...


class HallReservationService(IHallReservationService):
    def __init__(
        self,
        repository: IHallRepository,
        membership_repository: IUnitMembershipRepository,
        email_sender: IEmailSender,
    ):
        self._repo = repository
        self._memberships = membership_repository
        self._email = email_sender

    def list(self, user, status=None):
        normalized = self._normalize_status_filter(status)
        return self._repo.list_all(
            status=normalized,
            condominium_id=require_condominium_id(user),
        )

    @staticmethod
    def _normalize_status_filter(status: str | None) -> str | None:
        if not status:
            return None
        upper = status.upper()
        valid = {s.value for s in HallReservationModel.Status}
        if upper not in valid:
            raise BusinessRuleError(
                f"Invalid status filter: {status!r}. "
                f"Expected one of {sorted(valid)}.",
                field="status",
            )
        return upper

    def get(self, user, pk):
        instance = self._repo.get_by_id(pk)
        if not instance:
            raise NotFoundError("No Hall reservation matches the given query.")
        assert_same_condominium(user, instance.unit.condominium_id)
        return instance

    def create(self, user, payload: dict):
        ensure_not_employee(user, action="book reservations")
        data = dict(payload)
        reservation_user = self._resolve_reservation_user(
            user, data.get("reservation_user")
        )
        unit = self._resolve_unit(reservation_user)
        data["reservation_user"] = reservation_user
        data["unit"] = unit

        reservation_date = data.get("reservation_date")
        start_time = data.get("start_time")
        end_time = data.get("end_time")
        self._validate_date(reservation_date)
        self._validate_slot(user, reservation_date, start_time, end_time)

        # Admin bookings skip the approval queue; everyone else lands
        # as PENDING and waits for an admin to approve/reject.
        data["status"] = (
            HallReservationModel.Status.APPROVED
            if user.is_staff
            else HallReservationModel.Status.PENDING
        )

        return self._repo.create(data)

    def update(self, user, pk, payload):
        ensure_not_employee(user, action="book reservations")
        instance = self.get(user, pk)
        return self._repo.update(instance, payload)

    def delete(self, user, pk):
        ensure_not_employee(user, action="book reservations")
        instance = self.get(user, pk)
        self._repo.delete(instance)

    def approve(self, user, pk):
        if not user.is_staff:
            raise PermissionDeniedError(
                "Only admins can approve a hall booking."
            )
        instance = self.get(user, pk)
        if instance.status == HallReservationModel.Status.APPROVED:
            return instance
        # Re-validate against the current state of APPROVED bookings.
        self._validate_date(instance.reservation_date)
        self._validate_slot(
            user,
            instance.reservation_date,
            instance.start_time,
            instance.end_time,
        )
        updated = self._repo.update(
            instance, {"status": HallReservationModel.Status.APPROVED}
        )
        self._notify_reservation_approved(updated, resource_name="party hall")
        return updated

    def reject(self, user, pk, reason=""):
        if not user.is_staff:
            raise PermissionDeniedError(
                "Only admins can reject a hall booking."
            )
        if not reason or not reason.strip():
            raise BusinessRuleError(
                "A rejection reason is required.", field="reason"
            )
        instance = self.get(user, pk)
        if instance.status == HallReservationModel.Status.REJECTED:
            return instance
        updated = self._repo.update(
            instance, {"status": HallReservationModel.Status.REJECTED}
        )
        self._notify_reservation_rejected(
            updated, resource_name="party hall", reason=reason
        )
        return updated

    # --- internal rules ----------------------------------------------- #
    def _notify_reservation_approved(self, instance, resource_name: str) -> None:
        user = instance.reservation_user
        if not user or not getattr(user, "email", None):
            return
        self._email.send_reservation_approved(
            to_email=user.email,
            user_name=getattr(user, "full_name", None) or user.username,
            resource_name=resource_name,
            reservation_date=instance.reservation_date,
            start_time=instance.start_time,
            end_time=instance.end_time,
        )

    def _notify_reservation_rejected(
        self, instance, resource_name: str, reason: str = ""
    ) -> None:
        user = instance.reservation_user
        if not user or not getattr(user, "email", None):
            return
        self._email.send_reservation_rejected(
            to_email=user.email,
            user_name=getattr(user, "full_name", None) or user.username,
            resource_name=resource_name,
            reservation_date=instance.reservation_date,
            start_time=instance.start_time,
            end_time=instance.end_time,
            reason=reason,
        )

    def _resolve_reservation_user(self, requester, passed_user):
        if requester.is_staff:
            if not passed_user:
                raise BusinessRuleError(
                    "reservation_user can not be empty."
                )
            return passed_user
        if passed_user and passed_user.id != requester.id:
            raise BusinessRuleError("You can not pass a reservation_user.")
        return requester

    def _resolve_unit(self, target_user):
        memberships = [
            m
            for m in self._memberships.list_active_for_user(target_user.id)
            if m.status == UnitMembership.Status.ACTIVE
        ]
        if not memberships:
            raise BusinessRuleError(
                "User must belong to an active unit to book the hall."
            )
        return memberships[0].unit

    def _validate_date(self, reservation_date: date):
        if reservation_date < date.today():
            raise BusinessRuleError(
                "You can not book in a past day.", field="reservation_date"
            )

    def _validate_slot(
        self,
        user,
        reservation_date: date,
        start_time: time | None,
        end_time: time | None,
    ):
        """Enforce slot sanity, overlap, and the 30-minute gap rule.

        Semantics:
          - missing ``start_time`` → 00:00:00
          - missing ``end_time``   → 23:59:59
          - ``start_time >= end_time`` is invalid.
          - Two APPROVED reservations on the same day must not overlap.
          - There must be at least 30 minutes between one ending and
            the next starting.
        """
        if start_time and end_time and start_time >= end_time:
            raise BusinessRuleError(
                "start_time must be earlier than end_time.",
                field="start_time",
            )
        for existing in self._repo.list_for_date(
            reservation_date,
            condominium_id=require_condominium_id(user),
        ):
            if slots_overlap(
                start_time, end_time,
                existing.start_time, existing.end_time,
            ):
                raise BusinessRuleError(
                    "The Hall already has a booking in this time window.",
                    field="reservation_date",
                )
            if slots_too_close(
                start_time, end_time,
                existing.start_time, existing.end_time,
            ):
                raise BusinessRuleError(
                    "Hall reservations must be at least 30 minutes "
                    "apart. One ends and the next starts too close "
                    "together.",
                    field="start_time",
                )
