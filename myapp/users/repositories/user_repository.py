"""Dumb repository for the auth User model. Pure ORM access."""

from abc import ABC, abstractmethod
from typing import Iterable

from django.contrib.auth import get_user_model


class IUserRepository(ABC):
    @abstractmethod
    def list_all(self) -> Iterable: ...

    @abstractmethod
    def get_by_id(self, pk: int): ...

    @abstractmethod
    def exists_with_email(self, email: str) -> bool: ...

    @abstractmethod
    def exists_with_username(self, username: str) -> bool: ...

    @abstractmethod
    def exists_with_cpf(self, cpf: str) -> bool: ...

    @abstractmethod
    def create_user(self, **fields): ...

    @abstractmethod
    def update(self, instance, data: dict): ...

    @abstractmethod
    def delete(self, instance) -> None: ...


class DjangoUserRepository(IUserRepository):
    def _model(self):
        return get_user_model()

    def list_all(self):
        return self._model().objects.all().order_by("id")

    def get_by_id(self, pk):
        return self._model().objects.filter(pk=pk).first()

    def exists_with_email(self, email):
        return self._model().objects.filter(email__iexact=email).exists()

    def exists_with_username(self, username):
        return self._model().objects.filter(username=username).exists()

    def exists_with_cpf(self, cpf):
        return self._model().objects.filter(cpf=cpf).exists()

    def create_user(self, **fields):
        password = fields.pop("password")
        username = fields.pop("username")
        return self._model().objects.create_user(
            username=username, password=password, **fields
        )

    def update(self, instance, data):
        for k, v in data.items():
            if k == "password":
                instance.set_password(v)
            else:
                setattr(instance, k, v)
        instance.save()
        return instance

    def delete(self, instance):
        instance.delete()
