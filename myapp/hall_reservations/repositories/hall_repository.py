"""Dumb repository for HallReservationModel."""

from abc import ABC, abstractmethod
from datetime import date

from hall_reservations.models import HallReservationModel


class IHallRepository(ABC):
    @abstractmethod
    def list_all(self, status: str | None = None): ...

    @abstractmethod
    def get_by_id(self, pk: int) -> HallReservationModel | None: ...

    @abstractmethod
    def list_for_date(self, reservation_date: date): ...

    @abstractmethod
    def latest_date_for_household(self, household_id: int) -> date | None: ...

    @abstractmethod
    def create(self, data: dict) -> HallReservationModel: ...

    @abstractmethod
    def update(self, instance: HallReservationModel, data: dict) -> HallReservationModel: ...

    @abstractmethod
    def delete(self, instance: HallReservationModel) -> None: ...

    @abstractmethod
    def count_by_status(self, status: str | None = None) -> int: ...


class DjangoHallRepository(IHallRepository):
    def list_all(self, status=None):
        qs = (
            HallReservationModel.objects.all()
            .select_related("reservation_user", "household")
            .order_by("-reservation_date")
        )
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_by_id(self, pk):
        return (
            HallReservationModel.objects
            .select_related("reservation_user", "household")
            .filter(pk=pk)
            .first()
        )

    def list_for_date(self, reservation_date):
        """Only APPROVED bookings occupy a time slot."""
        return HallReservationModel.objects.filter(
            reservation_date=reservation_date,
            status=HallReservationModel.Status.APPROVED,
        ).only("id", "start_time", "end_time", "reservation_date")

    def latest_date_for_household(self, household_id):
        """Only APPROVED bookings count toward the 30-day cool-down."""
        last = (
            HallReservationModel.objects.filter(
                household_id=household_id,
                status=HallReservationModel.Status.APPROVED,
            )
            .order_by("-reservation_date")
            .first()
        )
        return last.reservation_date if last else None

    def create(self, data):
        return HallReservationModel.objects.create(**data)

    def update(self, instance, data):
        for k, v in data.items():
            setattr(instance, k, v)
        instance.save()
        return instance

    def delete(self, instance):
        instance.delete()

    def count_by_status(self, status=None):
        qs = HallReservationModel.objects.all()
        if status:
            qs = qs.filter(status=status)
        return qs.count()
