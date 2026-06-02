"""Business rules for users."""

from abc import ABC, abstractmethod

from shared.exceptions import BusinessRuleError, NotFoundError, PermissionDeniedError
from shared.infrastructure.document_validators import (
    ICPFValidator,
    IPhoneValidator,
)
from shared.infrastructure.password_policy import IPasswordPolicy
from users.models import UserRole
from users.repositories.user_repository import IUserRepository


_IMMUTABLE_ON_PATCH = {"username", "cpf"}
_VALID_ROLES = {choice for choice, _ in UserRole.choices}


class IUserService(ABC):
    @abstractmethod
    def list_for(self, user, role: str | None = None): ...

    @abstractmethod
    def get_for(self, user, pk: int): ...

    @abstractmethod
    def create(self, requester, payload: dict, *, is_active: bool = True): ...

    @abstractmethod
    def activate(self, user) -> None: ...

    @abstractmethod
    def hard_delete(self, user) -> None: ...

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

    def list_for(self, user, role=None):
        if not user.is_staff:
            return [user]
        if role is not None:
            if role not in _VALID_ROLES:
                raise BusinessRuleError(
                    message=f"Invalid role filter: {role!r}.", field="role"
                )
            return self._repo.list_by_role(role)
        return self._repo.list_all()

    def get_for(self, user, pk):
        instance = self._repo.get_by_id(pk)
        if not instance:
            raise NotFoundError("No user matches the given query.")
        if not user.is_staff and instance.id != user.id:
            raise NotFoundError("No user matches the given query.")
        return instance

    def activate(self, user) -> None:
        self._repo.set_active(user, True)

    def hard_delete(self, user) -> None:
        self._repo.delete(user)

    def create(self, requester, payload: dict, *, is_active: bool = True):
        is_anonymous = requester is None or not getattr(
            requester, "is_authenticated", False
        )
        if not is_anonymous and not getattr(requester, "is_staff", False):
            raise PermissionDeniedError(
                "Only anonymous users or staff can create accounts."
            )

        role = payload.pop("role", UserRole.RESIDENT)
        if role not in _VALID_ROLES:
            raise BusinessRuleError(
                message=f"Invalid role: {role!r}.", field="role"
            )
        if role != UserRole.RESIDENT and is_anonymous:
            raise PermissionDeniedError(
                "Only admins can create non-resident users."
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
            apartment=payload.get("apartment", ""),
            block=payload.get("block", ""),
            photo=payload.get("photo"),
            is_active=is_active,
            role=role,
            is_staff=role == UserRole.ADMIN,
        )

    def update(self, user, pk, payload):
        instance = self.get_for(user, pk)
        return self._update(user, instance, payload)

    def update_self(self, user, payload):
        return self._update(user, user, payload)

    def _update(self, requester, instance, payload):
        for field in _IMMUTABLE_ON_PATCH & payload.keys():
            payload.pop(field)

        if "role" in payload:
            new_role = payload["role"]
            if not getattr(requester, "is_staff", False):
                raise PermissionDeniedError("Only admins can change user role.")
            if new_role not in _VALID_ROLES:
                raise BusinessRuleError(
                    message=f"Invalid role: {new_role!r}.", field="role"
                )
            if (
                requester.id == instance.id
                and instance.role == UserRole.ADMIN
                and new_role != UserRole.ADMIN
            ):
                raise PermissionDeniedError(
                    "Admins cannot demote themselves."
                )
            payload["is_staff"] = new_role == UserRole.ADMIN

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
        if (
            user.id == instance.id
            and getattr(instance, "role", None) == UserRole.ADMIN
        ):
            raise PermissionDeniedError("Admins cannot delete themselves.")
        self._repo.delete(instance)
