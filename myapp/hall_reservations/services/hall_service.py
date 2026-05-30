"""Business rules for Hall reservations."""

from abc import ABC, abstractmethod
from datetime import date, timedelta

from hall_reservations.models import HallReservationModel
from hall_reservations.repositories.hall_repository import IHallRepository
from shared.exceptions import BusinessRuleError, NotFoundError


class IHallReservationService(ABC):
    @abstractmethod
    def list(self): ...

    @abstractmethod
    def get(self, pk: int) -> HallReservationModel: ...

    @abstractmethod
    def create(self, user, payload: dict) -> HallReservationModel: ...

    @abstractmethod
    def update(self, user, pk: int, payload: dict) -> HallReservationModel: ...

    @abstractmethod
    def delete(self, pk: int) -> None: ...


class HallReservationService(IHallReservationService):
    MIN_DAYS_BETWEEN_BOOKINGS = 30

    def __init__(self, repository: IHallRepository):
        self._repo = repository

    def list(self):
        return self._repo.list_all()

    def get(self, pk):
        instance = self._repo.get_by_id(pk)
        if not instance:
            raise NotFoundError("No Hall reservation matches the given query.")
        return instance

    def create(self, user, payload: dict):
        data = dict(payload)
        reservation_user = self._resolve_reservation_user(user, data.get("reservation_user"))
        data["reservation_user"] = reservation_user

        reservation_date = data.get("reservation_date")
        self._validate_date(reservation_date)

        if not user.is_staff:
            self._validate_30_day_window(reservation_user.id, reservation_date)

        return self._repo.create(data)

    def update(self, user, pk, payload):
        instance = self.get(pk)
        return self._repo.update(instance, payload)

    def delete(self, pk):
        instance = self.get(pk)
        self._repo.delete(instance)

    # --- internal rules ----------------------------------------------- #
    def _resolve_reservation_user(self, requester, passed_user):
        if not requester.is_staff:
            if passed_user:
                raise BusinessRuleError("You can not pass a reservation_user.")
            return requester
        if not passed_user:
            raise BusinessRuleError("reservation_user can not be empty.")
        return passed_user

    def _validate_date(self, reservation_date: date):
        if reservation_date < date.today():
            raise BusinessRuleError(
                "You can not book in a past day.", field="reservation_date"
            )
        if self._repo.exists_for_date(reservation_date):
            raise BusinessRuleError(
                "The Hall has already been booked.",
                field="reservation_date",
            )

    def _validate_30_day_window(self, user_id: int, reservation_date: date):
        last_date = self._repo.latest_date_for_user(user_id)
        if not last_date:
            return
        if reservation_date - last_date < timedelta(days=self.MIN_DAYS_BETWEEN_BOOKINGS):
            raise BusinessRuleError(
                "You can not book the hall with less than 30 days before your last bookment."
            )
