"""Business rules for users."""

from abc import ABC, abstractmethod

from shared.exceptions import BusinessRuleError, NotFoundError, PermissionDeniedError
from shared.infrastructure.document_validators import (
    ICPFValidator,
    IPhoneValidator,
)
from shared.infrastructure.password_policy import IPasswordPolicy
from users.repositories.user_repository import IUserRepository


_IMMUTABLE_ON_PATCH = {"username", "cpf"}


class IUserService(ABC):
    @abstractmethod
    def list_for(self, user): ...

    @abstractmethod
    def get_for(self, user, pk: int): ...

    @abstractmethod
    def create(self, requester, payload: dict): ...

    @abstractmethod
    def update(self, user, pk: int, payload: dict): ...

    @abstractmethod
    def update_self(self, user, payload: dict): ...

    @abstractmethod
    def delete(self, user, pk: int) -> None: ...


class UserService(IUserService):
    def __init__(
        self,
        user_repository: IUserRepository,
        password_policy: IPasswordPolicy,
        cpf_validator: ICPFValidator,
        phone_validator: IPhoneValidator,
    ):
        self._repo = user_repository
        self._policy = password_policy
        self._cpf = cpf_validator
        self._phone = phone_validator

    def list_for(self, user):
        if user.is_staff:
            return self._repo.list_all()
        return [user]

    def get_for(self, user, pk):
        instance = self._repo.get_by_id(pk)
        if not instance:
            raise NotFoundError("No user matches the given query.")
        if not user.is_staff and instance.id != user.id:
            raise NotFoundError("No user matches the given query.")
        return instance

    def create(self, requester, payload: dict):
        is_anonymous = requester is None or not getattr(
            requester, "is_authenticated", False
        )
        if not is_anonymous and not getattr(requester, "is_staff", False):
            raise PermissionDeniedError(
                "Only anonymous users or staff can create accounts."
            )

        password = payload.get("password", "")
        errors = self._policy.validate(password)
        if errors:
            raise BusinessRuleError(message=errors, field="password")

        username = payload.get("username", "")
        if username and self._repo.exists_with_username(username):
            raise BusinessRuleError(
                message="A user with that username already exists.",
                field="username",
            )

        email = (payload.get("email") or "").lower().strip()
        if email and self._repo.exists_with_email(email):
            raise BusinessRuleError(
                message="An account with this email address already exists.",
                field="email",
            )

        cpf = self._cpf.normalize(payload.get("cpf", ""))
        cpf_error = self._cpf.validate(cpf)
        if cpf_error:
            raise BusinessRuleError(message=cpf_error, field="cpf")
        if self._repo.exists_with_cpf(cpf):
            raise BusinessRuleError(
                message="An account with this CPF already exists.", field="cpf"
            )

        phone = self._phone.normalize(payload.get("phone", ""))
        phone_error = self._phone.validate(phone)
        if phone_error:
            raise BusinessRuleError(message=phone_error, field="phone")

        return self._repo.create_user(
            username=username,
            password=password,
            email=email,
            full_name=payload["full_name"],
            birth_date=payload["birth_date"],
            cpf=cpf,
            phone=phone,
            apartment=payload["apartment"],
            block=payload.get("block", ""),
            photo=payload.get("photo"),
        )

    def update(self, user, pk, payload):
        instance = self.get_for(user, pk)
        return self._update(instance, payload)

    def update_self(self, user, payload):
        return self._update(user, payload)

    def _update(self, instance, payload):
        for field in _IMMUTABLE_ON_PATCH & payload.keys():
            payload.pop(field)

        if "password" in payload:
            errors = self._policy.validate(payload["password"])
            if errors:
                raise BusinessRuleError(message=errors, field="password")

        if "email" in payload and payload["email"]:
            payload["email"] = payload["email"].lower().strip()
            if (
                payload["email"] != instance.email
                and self._repo.exists_with_email(payload["email"])
            ):
                raise BusinessRuleError(
                    message="An account with this email address already exists.",
                    field="email",
                )

        if "phone" in payload and payload["phone"]:
            phone = self._phone.normalize(payload["phone"])
            phone_error = self._phone.validate(phone)
            if phone_error:
                raise BusinessRuleError(message=phone_error, field="phone")
            payload["phone"] = phone

        return self._repo.update(instance, payload)

    def delete(self, user, pk):
        instance = self.get_for(user, pk)
        self._repo.delete(instance)
