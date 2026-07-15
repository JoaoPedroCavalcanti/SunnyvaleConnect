"""Dumb repository for the auth User model. Pure ORM access."""

from abc import ABC, abstractmethod
from typing import Iterable

from django.contrib.auth import get_user_model

from shared.tenant import build_tenant_username


class IUserRepository(ABC):
    @abstractmethod
    def list_all(self, *, condominium_id: int | None = None) -> Iterable: ...

    @abstractmethod
    def list_by_role(self, role: str, *, condominium_id: int | None = None) -> Iterable: ...

    @abstractmethod
    def list_filtered(
        self,
        *,
        role: str | None = None,
        is_active: bool | None = None,
        employee_type: str | None = None,
        condominium_id: int | None = None,
    ) -> Iterable: ...

    @abstractmethod
    def get_by_id(self, pk: int): ...

    @abstractmethod
    def exists_with_email(self, email: str) -> bool: ...

    @abstractmethod
    def exists_with_username(
        self,
        username: str,
        *,
        condominium_code: str,
        exclude_id: int | None = None,
    ) -> bool: ...

    @abstractmethod
    def exists_with_cpf(
        self,
        cpf: str,
        *,
        condominium_id: int,
        exclude_id: int | None = None,
    ) -> bool: ...

    @abstractmethod
    def create_user(self, **fields): ...

    @abstractmethod
    def update(self, instance, data: dict): ...

    @abstractmethod
    def delete(self, instance) -> None: ...

    @abstractmethod
    def set_active(self, instance, value: bool): ...

    @abstractmethod
    def list_admin_emails(self, *, condominium_id: int) -> list[str]: ...

    @abstractmethod
    def get_by_email(self, email: str): ...

    @abstractmethod
    def get_by_username(self, username: str, *, condominium_code: str | None = None): ...

    @abstractmethod
    def check_password(self, instance, raw_password: str) -> bool: ...

    @abstractmethod
    def count_active(self, *, condominium_id: int | None = None) -> int: ...


class DjangoUserRepository(IUserRepository):
    def _model(self):
        return get_user_model()

    def _scoped(self, qs, *, condominium_id: int | None):
        if condominium_id is not None:
            qs = qs.filter(condominium_id=condominium_id)
        return qs

    def list_all(self, *, condominium_id=None):
        qs = self._model().objects.all()
        return self._scoped(qs, condominium_id=condominium_id).order_by("id")

    def list_by_role(self, role, *, condominium_id=None):
        qs = self._model().objects.filter(role=role)
        return self._scoped(qs, condominium_id=condominium_id).order_by("id")

    def list_filtered(
        self, *, role=None, is_active=None, employee_type=None, condominium_id=None
    ):
        qs = self._model().objects.all()
        if role is not None:
            qs = qs.filter(role=role)
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        if employee_type is not None:
            qs = qs.filter(employee_types__contains=[employee_type])
        return self._scoped(qs, condominium_id=condominium_id).order_by("id")

    def get_by_id(self, pk):
        return self._model().objects.filter(pk=pk).first()

    def exists_with_email(self, email):
        return self._model().objects.filter(email__iexact=email).exists()

    def exists_with_username(
        self, username, *, condominium_code, exclude_id=None
    ):
        storage_username = build_tenant_username(condominium_code, username)
        qs = self._model().objects.filter(username=storage_username)
        if exclude_id is not None:
            qs = qs.exclude(pk=exclude_id)
        return qs.exists()

    def exists_with_cpf(self, cpf, *, condominium_id, exclude_id=None):
        qs = self._model().objects.filter(
            condominium_id=condominium_id, cpf=cpf
        )
        if exclude_id is not None:
            qs = qs.exclude(pk=exclude_id)
        return qs.exists()

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

    def list_admin_emails(self, *, condominium_id):
        return list(
            self._model()
            .objects.filter(
                condominium_id=condominium_id,
                is_staff=True,
                is_active=True,
            )
            .exclude(email="")
            .values_list("email", flat=True)
        )

    def get_by_email(self, email):
        return (
            self._model()
            .objects.select_related("condominium")
            .filter(email__iexact=email)
            .first()
        )

    def get_by_username(self, username, *, condominium_code=None):
        if condominium_code:
            username = build_tenant_username(condominium_code, username)
        return self._model().objects.filter(username=username).first()

    def check_password(self, instance, raw_password):
        return instance.check_password(raw_password)

    def count_active(self, *, condominium_id=None):
        qs = self._model().objects.filter(is_active=True)
        return self._scoped(qs, condominium_id=condominium_id).count()
