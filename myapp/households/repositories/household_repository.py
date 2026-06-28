"""Dumb repository for Household. Pure ORM access."""

from abc import ABC, abstractmethod
from typing import Iterable

from households.models import Household


class IHouseholdRepository(ABC):
    @abstractmethod
    def list_all(
        self, status: str | None = None, *, condominium_id: int | None = None
    ) -> Iterable[Household]: ...

    @abstractmethod
    def get_by_id(self, pk: int) -> Household | None: ...

    @abstractmethod
    def get_by_apartment_block(
        self, apartment: str, block: str, *, condominium_id: int
    ) -> Household | None: ...

    @abstractmethod
    def search(
        self,
        apartment: str | None,
        block: str | None,
        *,
        condominium_id: int,
    ) -> Iterable[Household]: ...

    @abstractmethod
    def create(self, data: dict) -> Household: ...

    @abstractmethod
    def update(self, instance: Household, data: dict) -> Household: ...

    @abstractmethod
    def delete(self, instance: Household) -> None: ...


class DjangoHouseholdRepository(IHouseholdRepository):
    def list_all(self, status=None, *, condominium_id=None):
        qs = Household.objects.all()
        if condominium_id is not None:
            qs = qs.filter(condominium_id=condominium_id)
        if status:
            qs = qs.filter(status=status)
        return qs.order_by("block", "apartment")

    def get_by_id(self, pk):
        return Household.objects.filter(pk=pk).first()

    def get_by_apartment_block(self, apartment, block, *, condominium_id):
        return Household.objects.filter(
            condominium_id=condominium_id,
            apartment=apartment,
            block=block,
        ).first()

    def search(self, apartment, block, *, condominium_id):
        qs = Household.objects.filter(condominium_id=condominium_id).exclude(
            status=Household.Status.ARCHIVED
        )
        if apartment:
            qs = qs.filter(apartment__iexact=apartment)
        if block:
            qs = qs.filter(block__iexact=block)
        return qs.order_by("block", "apartment")

    def create(self, data):
        return Household.objects.create(**data)

    def update(self, instance, data):
        for k, v in data.items():
            setattr(instance, k, v)
        instance.save()
        return instance

    def delete(self, instance):
        instance.delete()
