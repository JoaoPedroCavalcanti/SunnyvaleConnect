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
    def list_approved_between(
        self, from_date: date, to_date: date, *, condominium_id: int
    ): ...

    @abstractmethod
    def list_pending_for_user_between(
        self,
        user_id: int,
        from_date: date,
        to_date: date,
        *,
        condominium_id: int,
    ): ...

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

    def list_approved_between(self, from_date, to_date, *, condominium_id):
        return (
            HallReservationModel.objects.filter(
                reservation_date__gte=from_date,
                reservation_date__lte=to_date,
                status=HallReservationModel.Status.APPROVED,
                unit__condominium_id=condominium_id,
            )
            .select_related("reservation_user", "unit")
            .order_by("reservation_date", "start_time", "id")
        )

    def list_pending_for_user_between(
        self, user_id, from_date, to_date, *, condominium_id
    ):
        return (
            HallReservationModel.objects.filter(
                reservation_user_id=user_id,
                reservation_date__gte=from_date,
                reservation_date__lte=to_date,
                status=HallReservationModel.Status.PENDING,
                unit__condominium_id=condominium_id,
            )
            .select_related("reservation_user", "unit")
            .order_by("reservation_date", "start_time", "id")
        )

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
