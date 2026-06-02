"""Business rules for BBQ reservations.

A booking belongs to a *household* (the apartment), not to an
individual. The 30-day cool-down window and the "one booking per
apartment per month" rule are therefore enforced per household — any
member of the same apartment shares the cool-down.
"""

from abc import ABC, abstractmethod
from datetime import date, timedelta

from bbq_reservations.models import BBQReservationModel
from bbq_reservations.repositories.bbq_repository import IBBQRepository
from households.models import HouseholdMembership
from households.repositories.membership_repository import IMembershipRepository
from shared.exceptions import BusinessRuleError, NotFoundError


class IBBQReservationService(ABC):
    @abstractmethod
    def list(self): ...

    @abstractmethod
    def get(self, pk: int) -> BBQReservationModel: ...

    @abstractmethod
    def create(self, user, payload: dict) -> BBQReservationModel: ...

    @abstractmethod
    def update(self, user, pk: int, payload: dict) -> BBQReservationModel: ...

    @abstractmethod
    def delete(self, pk: int) -> None: ...


class BBQReservationService(IBBQReservationService):
    MIN_DAYS_BETWEEN_BOOKINGS = 30

    def __init__(
        self,
        repository: IBBQRepository,
        membership_repository: IMembershipRepository,
    ):
        self._repo = repository
        self._memberships = membership_repository

    def list(self):
        return self._repo.list_all()

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
        self._validate_date(reservation_date)

        if not user.is_staff:
            self._validate_30_day_window(household.id, reservation_date)

        return self._repo.create(data)

    def update(self, user, pk, payload):
        instance = self.get(pk)
        return self._repo.update(instance, payload)

    def delete(self, pk):
        instance = self.get(pk)
        self._repo.delete(instance)

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
                "The date is invalid.", field="reservation_date"
            )
        if self._repo.exists_for_date(reservation_date):
            raise BusinessRuleError(
                "The Barbecue has already been booked.",
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
