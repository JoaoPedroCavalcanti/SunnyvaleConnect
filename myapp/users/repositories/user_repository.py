"""Dumb repository for the auth User model. Pure ORM access."""

from abc import ABC, abstractmethod
from typing import Iterable

from django.contrib.auth import get_user_model


class IUserRepository(ABC):
    @abstractmethod
    def list_all(self) -> Iterable: ...

    @abstractmethod
    def list_by_role(self, role: str) -> Iterable: ...

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

    @abstractmethod
    def set_active(self, instance, value: bool): ...

    @abstractmethod
    def list_admin_emails(self) -> list[str]: ...

    @abstractmethod
    def get_by_username(self, username: str): ...

    @abstractmethod
    def check_password(self, instance, raw_password: str) -> bool: ...

    @abstractmethod
    def count_active(self) -> int: ...


class DjangoUserRepository(IUserRepository):
    def _model(self):
        return get_user_model()

    def list_all(self):
        return self._model().objects.all().order_by("id")

    def list_by_role(self, role):
        return self._model().objects.filter(role=role).order_by("id")

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

    def set_active(self, instance, value):
        instance.is_active = value
        instance.save(update_fields=["is_active"])
        return instance

    def list_admin_emails(self):
        return list(
            self._model()
            .objects.filter(is_staff=True, is_active=True)
            .exclude(email="")
            .values_list("email", flat=True)
        )

    def get_by_username(self, username):
        return self._model().objects.filter(username=username).first()

    def check_password(self, instance, raw_password):
        return instance.check_password(raw_password)

    def count_active(self):
        return self._model().objects.filter(is_active=True).count()
