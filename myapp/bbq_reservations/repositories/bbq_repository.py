"""Dumb repository for BBQReservationModel."""

from abc import ABC, abstractmethod
from datetime import date

from bbq_reservations.models import BBQReservationModel


class IBBQRepository(ABC):
    @abstractmethod
    def list_all(self): ...

    @abstractmethod
    def get_by_id(self, pk: int) -> BBQReservationModel | None: ...

    @abstractmethod
    def exists_for_date(self, reservation_date: date) -> bool: ...

    @abstractmethod
    def latest_date_for_user(self, user_id: int) -> date | None: ...

    @abstractmethod
    def create(self, data: dict) -> BBQReservationModel: ...

    @abstractmethod
    def update(self, instance: BBQReservationModel, data: dict) -> BBQReservationModel: ...

    @abstractmethod
    def delete(self, instance: BBQReservationModel) -> None: ...


class DjangoBBQRepository(IBBQRepository):
    def list_all(self):
        return BBQReservationModel.objects.all().order_by("-reservation_date")

    def get_by_id(self, pk):
        return BBQReservationModel.objects.filter(pk=pk).first()

    def exists_for_date(self, reservation_date):
        return BBQReservationModel.objects.filter(
            reservation_date=reservation_date
        ).exists()

    def latest_date_for_user(self, user_id):
        last = (
            BBQReservationModel.objects.filter(reservation_user_id=user_id)
            .order_by("-reservation_date")
            .first()
        )
        return last.reservation_date if last else None

    def create(self, data):
        return BBQReservationModel.objects.create(**data)

    def update(self, instance, data):
        for k, v in data.items():
            setattr(instance, k, v)
        instance.save()
        return instance

    def delete(self, instance):
        instance.delete()
