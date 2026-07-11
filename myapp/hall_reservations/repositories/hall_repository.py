"""Dumb repository for HallReservationModel."""

from abc import ABC, abstractmethod
from datetime import date

from hall_reservations.models import HallReservationModel


class IHallRepository(ABC):
    @abstractmethod
    def list_all(self, status: str | None = None, *, condominium_id: int): ...

    @abstractmethod
    def get_by_id(self, pk: int) -> HallReservationModel | None: ...

    @abstractmethod
    def list_for_date(self, reservation_date: date, *, condominium_id: int): ...

    @abstractmethod
    def create(self, data: dict) -> HallReservationModel: ...

    @abstractmethod
    def update(self, instance: HallReservationModel, data: dict) -> HallReservationModel: ...

    @abstractmethod
    def delete(self, instance: HallReservationModel) -> None: ...

    @abstractmethod
    def count_by_status(self, status: str | None = None, *, condominium_id: int) -> int: ...


class DjangoHallRepository(IHallRepository):
    def list_all(self, status=None, *, condominium_id):
        qs = (
            HallReservationModel.objects.filter(unit__condominium_id=condominium_id)
            .select_related("reservation_user", "unit")
            .order_by("-reservation_date")
        )
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_by_id(self, pk):
        return (
            HallReservationModel.objects
            .select_related("reservation_user", "unit")
            .filter(pk=pk)
            .first()
        )

    def list_for_date(self, reservation_date, *, condominium_id):
        """Only APPROVED bookings occupy a time slot."""
        return HallReservationModel.objects.filter(
            reservation_date=reservation_date,
            status=HallReservationModel.Status.APPROVED,
            unit__condominium_id=condominium_id,
        ).only("id", "start_time", "end_time", "reservation_date")

    def create(self, data):
        return HallReservationModel.objects.create(**data)

    def update(self, instance, data):
        for k, v in data.items():
            setattr(instance, k, v)
        instance.save()
        return instance

    def delete(self, instance):
        instance.delete()

    def count_by_status(self, status=None, *, condominium_id):
        qs = HallReservationModel.objects.filter(
            unit__condominium_id=condominium_id
        )
        if status:
            qs = qs.filter(status=status)
        return qs.count()
