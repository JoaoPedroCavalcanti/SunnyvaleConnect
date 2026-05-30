"""Dumb repository for HallReservationModel."""

from abc import ABC, abstractmethod
from datetime import date

from hall_reservations.models import HallReservationModel


class IHallRepository(ABC):
    @abstractmethod
    def list_all(self): ...

    @abstractmethod
    def get_by_id(self, pk: int) -> HallReservationModel | None: ...

    @abstractmethod
    def exists_for_date(self, reservation_date: date) -> bool: ...

    @abstractmethod
    def latest_date_for_user(self, user_id: int) -> date | None: ...

    @abstractmethod
    def create(self, data: dict) -> HallReservationModel: ...

    @abstractmethod
    def update(self, instance: HallReservationModel, data: dict) -> HallReservationModel: ...

    @abstractmethod
    def delete(self, instance: HallReservationModel) -> None: ...


class DjangoHallRepository(IHallRepository):
    def list_all(self):
        return HallReservationModel.objects.all().order_by("-reservation_date")

    def get_by_id(self, pk):
        return HallReservationModel.objects.filter(pk=pk).first()

    def exists_for_date(self, reservation_date):
        return HallReservationModel.objects.filter(
            reservation_date=reservation_date
        ).exists()

    def latest_date_for_user(self, user_id):
        last = (
            HallReservationModel.objects.filter(reservation_user_id=user_id)
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
