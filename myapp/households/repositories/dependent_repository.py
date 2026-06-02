"""Dumb repository for Dependent. Pure ORM access."""

from abc import ABC, abstractmethod
from typing import Iterable

from households.models import Dependent


class IDependentRepository(ABC):
    @abstractmethod
    def list_for_household(self, household_id: int) -> Iterable[Dependent]: ...

    @abstractmethod
    def get_by_id(self, pk: int) -> Dependent | None: ...

    @abstractmethod
    def exists_active_with_cpf(self, cpf: str) -> bool: ...

    @abstractmethod
    def create(self, data: dict) -> Dependent: ...

    @abstractmethod
    def update(self, instance: Dependent, data: dict) -> Dependent: ...

    @abstractmethod
    def soft_delete(self, instance: Dependent) -> Dependent: ...


class DjangoDependentRepository(IDependentRepository):
    def list_for_household(self, household_id):
        return Dependent.objects.filter(
            household_id=household_id, is_active=True
        ).order_by("full_name")

    def get_by_id(self, pk):
        return Dependent.objects.filter(pk=pk).first()

    def exists_active_with_cpf(self, cpf):
        if not cpf:
            return False
        return Dependent.objects.filter(cpf=cpf, is_active=True).exists()

    def create(self, data):
        return Dependent.objects.create(**data)

    def update(self, instance, data):
        for k, v in data.items():
            setattr(instance, k, v)
        instance.save()
        return instance

    def soft_delete(self, instance):
        instance.is_active = False
        instance.save()
        return instance
