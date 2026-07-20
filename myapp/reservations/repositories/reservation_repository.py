from abc import ABC, abstractmethod
from datetime import date, time

from django.db.models import Q

from reservations.models import Reservation


class IReservationRepository(ABC):
    @abstractmethod
    def list_for_condominium(
        self,
        condominium_id: int,
        *,
        status: str | None = None,
        period: str | None = None,
        reference: tuple[date, time] | None = None,
        location_id: int | None = None,
    ): ...

    @abstractmethod
    def list_for_user(
        self,
        user_id: int,
        condominium_id: int,
        *,
        status: str | None = None,
        period: str | None = None,
        reference: tuple[date, time] | None = None,
        location_id: int | None = None,
    ): ...

    @abstractmethod
    def get_by_id(self, pk: int) -> Reservation | None: ...

    @abstractmethod
    def list_blocking_for_location_date(
        self,
        location_id: int,
        reservation_date: date,
        *,
        exclude_id: int | None = None,
    ): ...

    @abstractmethod
    def list_blocking_between(
        self, location_id: int, from_date: date, to_date: date
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

    def list_for_condominium(
        self,
        condominium_id,
        *,
        status=None,
        period=None,
        reference=None,
        location_id=None,
    ):
        queryset = self._base().filter(condominium_id=condominium_id)
        if status:
            queryset = queryset.filter(status=status)
        if location_id is not None:
            queryset = queryset.filter(location_id=location_id)
        if period == "future" and reference:
            today, current_time = reference
            queryset = queryset.filter(
                Q(reservation_date__gt=today)
                | Q(
                    reservation_date=today,
                    end_time__gte=current_time,
                )
                | Q(reservation_date=today, end_time__isnull=True)
            )
        elif period == "past" and reference:
            today, current_time = reference
            queryset = queryset.filter(
                Q(reservation_date__lt=today)
                | Q(reservation_date=today, end_time__lt=current_time)
            )
        if period == "future":
            ordering = ("reservation_date", "start_time", "id")
        elif period == "past":
            ordering = ("-reservation_date", "-start_time", "-id")
        else:
            ordering = ("-reservation_date", "start_time", "id")
        return queryset.order_by(*ordering)

    def list_for_user(
        self,
        user_id,
        condominium_id,
        *,
        status=None,
        period=None,
        reference=None,
        location_id=None,
    ):
        queryset = self._base().filter(
            condominium_id=condominium_id,
            reservation_user_id=user_id,
        )
        if status:
            queryset = queryset.filter(status=status)
        if location_id is not None:
            queryset = queryset.filter(location_id=location_id)
        if period == "future" and reference:
            today, current_time = reference
            queryset = queryset.filter(
                Q(reservation_date__gt=today)
                | Q(
                    reservation_date=today,
                    end_time__gte=current_time,
                )
                | Q(reservation_date=today, end_time__isnull=True)
            )
        elif period == "past" and reference:
            today, current_time = reference
            queryset = queryset.filter(
                Q(reservation_date__lt=today)
                | Q(reservation_date=today, end_time__lt=current_time)
            )
        if period == "future":
            ordering = ("reservation_date", "start_time", "id")
        elif period == "past":
            ordering = ("-reservation_date", "-start_time", "-id")
        else:
            ordering = ("-reservation_date", "start_time", "id")
        return queryset.order_by(*ordering)

    def get_by_id(self, pk):
        return self._base().filter(pk=pk).first()

    def list_blocking_for_location_date(
        self, location_id, reservation_date, *, exclude_id=None
    ):
        queryset = Reservation.objects.filter(
            location_id=location_id,
            reservation_date=reservation_date,
            status__in=[
                Reservation.Status.PENDING,
                Reservation.Status.APPROVED,
            ],
        )
        if exclude_id is not None:
            queryset = queryset.exclude(pk=exclude_id)
        return queryset.only("id", "start_time", "end_time")

    def list_blocking_between(self, location_id, from_date, to_date):
        return (
            self._base()
            .filter(
                location_id=location_id,
                reservation_date__range=(from_date, to_date),
                status__in=[
                    Reservation.Status.PENDING,
                    Reservation.Status.APPROVED,
                ],
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
