"""Business rules for users."""

from abc import ABC, abstractmethod

from shared.exceptions import BusinessRuleError, NotFoundError, PermissionDeniedError
from shared.infrastructure.document_validators import (
    ICPFValidator,
    IPhoneValidator,
)
from shared.infrastructure.password_policy import IPasswordPolicy
from shared.roles import ensure_not_employee, is_admin, is_employee
from shared.tenant import (
    assert_same_condominium,
    build_tenant_username,
    is_platform_superuser,
    require_condominium_id,
)
from users.models import EmployeeType, UserRole
from users.repositories.user_repository import IUserRepository


_IMMUTABLE_ON_PATCH = {"username", "cpf"}
_VALID_ROLES = {choice for choice, _ in UserRole.choices}
_VALID_EMPLOYEE_TYPES = {choice for choice, _ in EmployeeType.choices}


class IUserService(ABC):
    @abstractmethod
    def list_for(
        self,
        user,
        role: str | None = None,
        *,
        is_active: bool | None = None,
        employee_type: str | None = None,
    ): ...

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

    def list_for(self, user, role=None, *, is_active=None, employee_type=None):
        if not is_admin(user):
            return [user]
        if role is not None and role not in _VALID_ROLES:
            raise BusinessRuleError(
                message=f"Invalid role filter: {role!r}.", field="role"
            )
        normalized_employee_type = None
        if employee_type is not None:
            normalized_employee_type = str(employee_type).upper()
            if normalized_employee_type not in _VALID_EMPLOYEE_TYPES:
                raise BusinessRuleError(
                    message=f"Invalid employee type filter: {employee_type!r}.",
                    field="employee_type",
                )
        return self._repo.list_filtered(
            role=role,
            is_active=is_active,
            employee_type=normalized_employee_type,
            condominium_id=require_condominium_id(user),
        )

    def get_for(self, user, pk):
        instance = self._repo.get_by_id(pk)
        if not instance:
            raise NotFoundError("No user matches the given query.")
        if not is_admin(user) and instance.id != user.id:
            raise NotFoundError("No user matches the given query.")
        assert_same_condominium(user, instance.condominium_id)
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

        condominium_id = payload.pop("condominium_id", None)
        condominium_code = payload.pop("condominium_code", None)
        if is_anonymous:
            if not condominium_id:
                raise BusinessRuleError(
                    "condominium_id is required for anonymous signup.",
                    field="condominium_code",
                )
        elif is_platform_superuser(requester):
            if not condominium_id:
                raise BusinessRuleError(
                    "condominium_id is required when creating users as superuser.",
                    field="condominium_id",
                )
        else:
            condominium_id = require_condominium_id(requester)
            condominium_code = requester.condominium.code

        password = payload.get("password", "")
        errors = self._policy.validate(password)
        if errors:
            raise BusinessRuleError(message=errors, field="password")

        username = payload.get("username", "")
        if username:
            if not condominium_code:
                raise BusinessRuleError(
                    "condominium_code is required to validate username.",
                    field="condominium_code",
                )
            if self._repo.exists_with_username(
                username, condominium_code=condominium_code
            ):
                raise BusinessRuleError(
                    message="A user with that username already exists.",
                    field="username",
                )
            payload["username"] = build_tenant_username(condominium_code, username)

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
        if self._repo.exists_with_cpf(cpf, condominium_id=condominium_id):
            raise BusinessRuleError(
                message="An account with this CPF already exists.", field="cpf"
            )

        phone = self._phone.normalize(payload.get("phone", ""))
        phone_error = self._phone.validate(phone)
        if phone_error:
            raise BusinessRuleError(message=phone_error, field="phone")

        employee_types = self._normalize_employee_types(
            role, payload.pop("employee_types", None)
        )
        apartment = payload.get("apartment", "") or ""
        block = payload.get("block", "") or ""
        if role == UserRole.EMPLOYEE and (apartment or block):
            raise BusinessRuleError(
                "Employees cannot be linked to an apartment.",
                field="apartment",
            )

        return self._repo.create_user(
            username=payload.get("username", username),
            password=password,
            email=email,
            full_name=payload["full_name"],
            birth_date=payload["birth_date"],
            cpf=cpf,
            phone=phone,
            apartment=apartment if role != UserRole.EMPLOYEE else "",
            block=block if role != UserRole.EMPLOYEE else "",
            photo=payload.get("photo"),
            is_active=is_active,
            role=role,
            is_staff=role == UserRole.ADMIN,
            employee_types=employee_types,
            condominium_id=condominium_id,
        )

    def update(self, user, pk, payload):
        instance = self.get_for(user, pk)
        return self._update(user, instance, payload)

    def update_self(self, user, payload):
        if is_employee(user):
            raise PermissionDeniedError(
                "Employees cannot edit their own profile."
            )
        return self._update(user, user, payload)

    def _update(self, requester, instance, payload):
        for field in _IMMUTABLE_ON_PATCH & payload.keys():
            payload.pop(field)

        if "is_active" in payload:
            if not getattr(requester, "is_staff", False):
                raise PermissionDeniedError("Only admins can change account status.")
            self._repo.set_active(instance, bool(payload.pop("is_active")))
            if not payload:
                return instance

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
            if new_role != UserRole.EMPLOYEE:
                payload["employee_types"] = []
            if new_role == UserRole.EMPLOYEE:
                payload.setdefault(
                    "employee_types",
                    list(getattr(instance, "employee_types", None) or []),
                )
                payload["apartment"] = ""
                payload["block"] = ""

        if "employee_types" in payload:
            if not getattr(requester, "is_staff", False):
                raise PermissionDeniedError(
                    "Only admins can change employee types."
                )
            effective_role = payload.get("role", instance.role)
            payload["employee_types"] = self._normalize_employee_types(
                effective_role, payload["employee_types"]
            )

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

        if getattr(instance, "role", None) == UserRole.EMPLOYEE:
            payload.pop("apartment", None)
            payload.pop("block", None)

        return self._repo.update(instance, payload)

    def delete(self, user, pk):
        instance = self.get_for(user, pk)
        if (
            user.id == instance.id
            and getattr(instance, "role", None) == UserRole.ADMIN
        ):
            raise PermissionDeniedError("Admins cannot delete themselves.")
        if getattr(instance, "role", None) == UserRole.EMPLOYEE:
            raise PermissionDeniedError(
                "Employees cannot be deleted. Deactivate the account instead."
            )
        self._repo.delete(instance)

    @staticmethod
    def _normalize_employee_types(role: str, raw) -> list[str]:
        if role != UserRole.EMPLOYEE:
            return []
        if raw is None:
            raise BusinessRuleError(
                "Employee accounts require at least one employee type.",
                field="employee_types",
            )
        if not isinstance(raw, (list, tuple)):
            raise BusinessRuleError(
                "employee_types must be a list.",
                field="employee_types",
            )
        normalized: list[str] = []
        for value in raw:
            upper = str(value).upper()
            if upper not in _VALID_EMPLOYEE_TYPES:
                raise BusinessRuleError(
                    message=f"Invalid employee type: {value!r}.",
                    field="employee_types",
                )
            if upper not in normalized:
                normalized.append(upper)
        if not normalized:
            raise BusinessRuleError(
                "Employee accounts require at least one employee type.",
                field="employee_types",
            )
        return normalized
