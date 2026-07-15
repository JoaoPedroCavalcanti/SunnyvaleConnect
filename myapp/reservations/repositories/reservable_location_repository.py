from abc import ABC, abstractmethod

from reservations.models import ReservableLocation


class IReservableLocationRepository(ABC):
    @abstractmethod
    def list_for_condominium(
        self, condominium_id: int, *, active_only: bool = True
    ): ...

    @abstractmethod
    def get_by_id(self, pk: int) -> ReservableLocation | None: ...

    @abstractmethod
    def exists_with_name(
        self,
        condominium_id: int,
        name: str,
        *,
        exclude_id: int | None = None,
    ) -> bool: ...

    @abstractmethod
    def create(self, data: dict) -> ReservableLocation: ...

    @abstractmethod
    def update(
        self, instance: ReservableLocation, data: dict
    ) -> ReservableLocation: ...


class DjangoReservableLocationRepository(IReservableLocationRepository):
    def list_for_condominium(self, condominium_id, *, active_only=True):
        queryset = ReservableLocation.objects.filter(
            condominium_id=condominium_id
        )
        if active_only:
            queryset = queryset.filter(is_active=True)
        return queryset.order_by("name", "id")

    def get_by_id(self, pk):
        return (
            ReservableLocation.objects.select_related("condominium")
            .filter(pk=pk)
            .first()
        )

    def exists_with_name(
        self, condominium_id, name, *, exclude_id=None
    ):
        queryset = ReservableLocation.objects.filter(
            condominium_id=condominium_id,
            name__iexact=name,
        )
        if exclude_id is not None:
            queryset = queryset.exclude(pk=exclude_id)
        return queryset.exists()

    def create(self, data):
        return ReservableLocation.objects.create(**data)

    def update(self, instance, data):
        for key, value in data.items():
            setattr(instance, key, value)
        instance.save()
        return instance
