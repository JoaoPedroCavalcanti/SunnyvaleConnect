"""Dumb repository for Condominium. Pure ORM access."""

from abc import ABC, abstractmethod
from typing import Iterable

from condominiums.models import Condominium


class ICondominiumRepository(ABC):
    @abstractmethod
    def list_all(self) -> Iterable[Condominium]: ...

    @abstractmethod
    def get_by_id(self, pk: int) -> Condominium | None: ...

    @abstractmethod
    def get_by_code(self, code: str) -> Condominium | None: ...

    @abstractmethod
    def exists_with_code(self, code: str) -> bool: ...

    @abstractmethod
    def create(self, data: dict) -> Condominium: ...

    @abstractmethod
    def update(self, instance: Condominium, data: dict) -> Condominium: ...


class DjangoCondominiumRepository(ICondominiumRepository):
    def list_all(self):
        return Condominium.objects.all().order_by("name")

    def get_by_id(self, pk):
        return Condominium.objects.filter(pk=pk).first()

    def get_by_code(self, code):
        normalized = (code or "").strip().upper()
        if not normalized:
            return None
        return Condominium.objects.filter(code__iexact=normalized).first()

    def exists_with_code(self, code):
        normalized = (code or "").strip().upper()
        if not normalized:
            return False
        return Condominium.objects.filter(code__iexact=normalized).exists()

    def create(self, data):
        return Condominium.objects.create(**data)

    def update(self, instance, data):
        for key, value in data.items():
            setattr(instance, key, value)
        instance.save()
        return instance
