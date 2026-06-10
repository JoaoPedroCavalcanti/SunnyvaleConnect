"""Business rules for BBQ reservations.

A booking belongs to a *household* (the apartment), not to an
individual. The 30-day cool-down window and the "one booking per
apartment per month" rule are therefore enforced per household — any
member of the same apartment shares the cool-down.
"""

from abc import ABC, abstractmethod
from datetime import date, time, timedelta

from bbq_reservations.models import BBQReservationModel
from bbq_reservations.repositories.bbq_repository import IBBQRepository
from households.models import HouseholdMembership
from households.repositories.membership_repository import IMembershipRepository
from shared.exceptions import (
    BusinessRuleError,
    NotFoundError,
    PermissionDeniedError,
)
from shared.time_slots import slots_overlap


class IBBQReservationService(ABC):
    @abstractmethod
    def list(self, status: str | None = None): ...

    @abstractmethod
    def get(self, pk: int) -> BBQReservationModel: ...

    @abstractmethod
    def create(self, user, payload: dict) -> BBQReservationModel: ...

    @abstractmethod
    def update(self, user, pk: int, payload: dict) -> BBQReservationModel: ...

    @abstractmethod
    def delete(self, pk: int) -> None: ...

    @abstractmethod
    def approve(self, user, pk: int) -> BBQReservationModel: ...

    @abstractmethod
    def reject(self, user, pk: int) -> BBQReservationModel: ...


class BBQReservationService(IBBQReservationService):
    MIN_DAYS_BETWEEN_BOOKINGS = 30

    def __init__(
        self,
        repository: IBBQRepository,
        membership_repository: IMembershipRepository,
    ):
        self._repo = repository
        self._memberships = membership_repository

    def list(self, status=None):
        normalized = self._normalize_status_filter(status)
        return self._repo.list_all(status=normalized)

    @staticmethod
    def _normalize_status_filter(status: str | None) -> str | None:
        if not status:
            return None
        upper = status.upper()
        valid = {s.value for s in BBQReservationModel.Status}
        if upper not in valid:
            raise BusinessRuleError(
                f"Invalid status filter: {status!r}. "
                f"Expected one of {sorted(valid)}.",
                field="status",
            )
        return upper

    def get(self, pk):
        instance = self._repo.get_by_id(pk)
        if not instance:
            raise NotFoundError("No BBQ reservation matches the given query.")
        return instance

    def create(self, user, payload: dict):
        data = dict(payload)
        reservation_user = self._resolve_reservation_user(
            user, data.get("reservation_user")
        )
        household = self._resolve_household(reservation_user)
        data["reservation_user"] = reservation_user
        data["household"] = household

        reservation_date = data.get("reservation_date")
        start_time = data.get("start_time")
        end_time = data.get("end_time")
        self._validate_date(reservation_date)
        self._validate_slot(reservation_date, start_time, end_time)

        if not user.is_staff:
            self._validate_30_day_window(household.id, reservation_date)

        # Admin bookings skip the approval queue; everyone else lands
        # as PENDING and waits for an admin to approve/reject.
        data["status"] = (
            BBQReservationModel.Status.APPROVED
            if user.is_staff
            else BBQReservationModel.Status.PENDING
        )

        return self._repo.create(data)

    def update(self, user, pk, payload):
        instance = self.get(pk)
        return self._repo.update(instance, payload)

    def delete(self, pk):
        instance = self.get(pk)
        self._repo.delete(instance)

    def approve(self, user, pk):
        if not user.is_staff:
            raise PermissionDeniedError(
                "Only admins can approve a barbecue booking."
            )
        instance = self.get(pk)
        if instance.status == BBQReservationModel.Status.APPROVED:
            return instance
        # Re-validate against the current state of APPROVED bookings:
        # other approvals may have happened since this one was created.
        self._validate_date(instance.reservation_date)
        self._validate_slot(
            instance.reservation_date,
            instance.start_time,
            instance.end_time,
        )
        if instance.household_id:
            self._validate_30_day_window(
                instance.household_id, instance.reservation_date
            )
        return self._repo.update(
            instance, {"status": BBQReservationModel.Status.APPROVED}
        )

    def reject(self, user, pk):
        if not user.is_staff:
            raise PermissionDeniedError(
                "Only admins can reject a barbecue booking."
            )
        instance = self.get(pk)
        if instance.status == BBQReservationModel.Status.REJECTED:
            return instance
        return self._repo.update(
            instance, {"status": BBQReservationModel.Status.REJECTED}
        )

    # --- internal rules ----------------------------------------------- #
    def _resolve_reservation_user(self, requester, passed_user):
        """Admin must pass the target user explicitly. Regular users
        always book for themselves; passing their own id is tolerated
        (front sends it automatically), passing someone else's id is
        rejected.
        """
        if requester.is_staff:
            if not passed_user:
                raise BusinessRuleError(
                    "reservation_user can not be empty."
                )
            return passed_user
        if passed_user and passed_user.id != requester.id:
            raise BusinessRuleError("You can not pass a reservation_user.")
        return requester

    def _resolve_household(self, target_user):
        memberships = [
            m
            for m in self._memberships.list_active_for_user(target_user.id)
            if m.status == HouseholdMembership.Status.ACTIVE
        ]
        if not memberships:
            raise BusinessRuleError(
                "User must belong to an active household to book the "
                "barbecue."
            )
        # If the user happens to be in more than one active household
        # (rare in practice), use the first deterministic match.
        return memberships[0].household

    def _validate_date(self, reservation_date: date):
        if reservation_date < date.today():
            raise BusinessRuleError(
                "You can not book the barbecue for a past date.",
                field="reservation_date",
            )

    def _validate_slot(
        self,
        reservation_date: date,
        start_time: time | None,
        end_time: time | None,
    ):
        """Enforce slot sanity and detect overlap with same-day bookings.

        Semantics:
          - missing ``start_time`` → 00:00:00
          - missing ``end_time``   → 23:59:59
          - ``start_time >= end_time`` is invalid.
          - Two reservations on the same day are allowed as long as their
            (normalized) intervals do not overlap. Adjacent intervals
            (one ends exactly when the next starts) are allowed.
        """
        if start_time and end_time and start_time >= end_time:
            raise BusinessRuleError(
                "start_time must be earlier than end_time.",
                field="start_time",
            )
        for existing in self._repo.list_for_date(reservation_date):
            if slots_overlap(
                start_time, end_time,
                existing.start_time, existing.end_time,
            ):
                raise BusinessRuleError(
                    "The Barbecue already has a booking in this time "
                    "window.",
                    field="reservation_date",
                )

    def _validate_30_day_window(
        self, household_id: int, reservation_date: date
    ):
        last_date = self._repo.latest_date_for_household(household_id)
        if not last_date:
            return
        if reservation_date - last_date < timedelta(
            days=self.MIN_DAYS_BETWEEN_BOOKINGS
        ):
            raise BusinessRuleError(
                "This apartment already booked the barbecue less than "
                f"{self.MIN_DAYS_BETWEEN_BOOKINGS} days ago."
            )
