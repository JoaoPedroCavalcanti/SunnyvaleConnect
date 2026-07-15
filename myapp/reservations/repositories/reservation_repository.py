from abc import ABC, abstractmethod
from datetime import date

from reservations.models import Reservation


class IReservationRepository(ABC):
    @abstractmethod
    def list_for_condominium(
        self, condominium_id: int, *, status: str | None = None
    ): ...

    @abstractmethod
    def list_for_user(
        self,
        user_id: int,
        condominium_id: int,
        *,
        status: str | None = None,
    ): ...

    @abstractmethod
    def get_by_id(self, pk: int) -> Reservation | None: ...

    @abstractmethod
    def list_approved_for_location_date(
        self,
        location_id: int,
        reservation_date: date,
        *,
        exclude_id: int | None = None,
    ): ...

    @abstractmethod
    def list_approved_between(
        self, location_id: int, from_date: date, to_date: date
    ): ...

    @abstractmethod
    def list_pending_for_user_between(
        self,
        location_id: int,
        user_id: int,
        from_date: date,
        to_date: date,
    ): ...

    @abstractmethod
    def count_by_status(
        self, status: str, *, condominium_id: int
    ) -> int: ...

    @abstractmethod
    def create(self, data: dict) -> Reservation: ...

    @abstractmethod
    def update(self, instance: Reservation, data: dict) -> Reservation: ...

    @abstractmethod
    def delete(self, instance: Reservation) -> None: ...


class DjangoReservationRepository(IReservationRepository):
    def _base(self):
        return Reservation.objects.select_related(
            "condominium", "location", "unit", "reservation_user"
        )

    def list_for_condominium(self, condominium_id, *, status=None):
        queryset = self._base().filter(condominium_id=condominium_id)
        if status:
            queryset = queryset.filter(status=status)
        return queryset.order_by("-reservation_date", "start_time", "id")

    def list_for_user(
        self, user_id, condominium_id, *, status=None
    ):
        queryset = self._base().filter(
            condominium_id=condominium_id,
            reservation_user_id=user_id,
        )
        if status:
            queryset = queryset.filter(status=status)
        return queryset.order_by("-reservation_date", "start_time", "id")

    def get_by_id(self, pk):
        return self._base().filter(pk=pk).first()

    def list_approved_for_location_date(
        self, location_id, reservation_date, *, exclude_id=None
    ):
        queryset = Reservation.objects.filter(
            location_id=location_id,
            reservation_date=reservation_date,
            status=Reservation.Status.APPROVED,
        )
        if exclude_id is not None:
            queryset = queryset.exclude(pk=exclude_id)
        return queryset.only("id", "start_time", "end_time")

    def list_approved_between(self, location_id, from_date, to_date):
        return (
            self._base()
            .filter(
                location_id=location_id,
                reservation_date__range=(from_date, to_date),
                status=Reservation.Status.APPROVED,
            )
            .order_by("reservation_date", "start_time", "id")
        )

    def list_pending_for_user_between(
        self, location_id, user_id, from_date, to_date
    ):
        return (
            self._base()
            .filter(
                location_id=location_id,
                reservation_user_id=user_id,
                reservation_date__range=(from_date, to_date),
                status=Reservation.Status.PENDING,
            )
            .order_by("reservation_date", "start_time", "id")
        )

    def count_by_status(self, status, *, condominium_id):
        return Reservation.objects.filter(
            condominium_id=condominium_id,
            status=status,
        ).count()

    def create(self, data):
        return Reservation.objects.create(**data)

    def update(self, instance, data):
        for key, value in data.items():
            setattr(instance, key, value)
        instance.save()
        return instance

    def delete(self, instance):
        instance.delete()
