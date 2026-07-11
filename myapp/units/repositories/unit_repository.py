"""Dumb repository for Unit. Pure ORM access."""

from abc import ABC, abstractmethod
from typing import Iterable

from units.models import Unit


class IUnitRepository(ABC):
    @abstractmethod
    def list_all(
        self, status: str | None = None, *, condominium_id: int | None = None
    ) -> Iterable[Unit]: ...

    @abstractmethod
    def get_by_id(self, pk: int) -> Unit | None: ...

    @abstractmethod
    def get_by_name(self, name: str, *, condominium_id: int) -> Unit | None: ...

    @abstractmethod
    def get_by_apartment(
        self, apartment: str, *, condominium_id: int
    ) -> Unit | None: ...

    @abstractmethod
    def get_by_apartment_block(
        self, apartment: str, block: str, *, condominium_id: int
    ) -> Unit | None: ...

    @abstractmethod
    def create(self, data: dict) -> Unit: ...

    @abstractmethod
    def update(self, instance: Unit, data: dict) -> Unit: ...

    @abstractmethod
    def delete(self, instance: Unit) -> None: ...


class DjangoUnitRepository(IUnitRepository):
    def list_all(self, status=None, *, condominium_id=None):
        qs = Unit.objects.all()
        if condominium_id is not None:
            qs = qs.filter(condominium_id=condominium_id)
        if status:
            qs = qs.filter(status=status)
        return qs.order_by("kind", "block", "apartment", "name")

    def get_by_id(self, pk):
        return Unit.objects.filter(pk=pk).first()

    def get_by_name(self, name, *, condominium_id):
        return Unit.objects.filter(
            condominium_id=condominium_id,
            kind=Unit.Kind.NAMED,
            name=name,
        ).first()

    def get_by_apartment(self, apartment, *, condominium_id):
        return Unit.objects.filter(
            condominium_id=condominium_id,
            kind=Unit.Kind.APARTMENT,
            apartment=apartment,
        ).first()

    def get_by_apartment_block(self, apartment, block, *, condominium_id):
        return Unit.objects.filter(
            condominium_id=condominium_id,
            kind=Unit.Kind.APARTMENT_BLOCK,
            apartment=apartment,
            block=block,
        ).first()

    def create(self, data):
        return Unit.objects.create(**data)

    def update(self, instance, data):
        for k, v in data.items():
            setattr(instance, k, v)
        instance.save()
        return instance

    def delete(self, instance):
        instance.delete()
