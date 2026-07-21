"""Business rules for users."""

from abc import ABC, abstractmethod

from shared.exceptions import BusinessRuleError, NotFoundError, PermissionDeniedError
from shared.infrastructure.document_validators import (
    ICPFValidator,
    IPhoneValidator,
)
from shared.infrastructure.password_policy import IPasswordPolicy
from shared.infrastructure.transactions import ITransactionRunner
from shared.roles import ensure_not_employee, is_admin, is_employee
from shared.tenant import (
    assert_same_condominium,
    build_tenant_username,
    is_platform_superuser,
    require_condominium_id,
)
from users.models import EmployeeType, UserRole
from users.repositories.user_repository import IUserRepository
from units.models import UnitMembership
from units.repositories.unit_membership_repository import (
    IUnitMembershipRepository,
)


_ADMIN_ONLY_PATCH_FIELDS = {"username", "cpf"}
_VALID_ROLES = {choice for choice, _ in UserRole.choices}
_VALID_EMPLOYEE_TYPES = {choice for choice, _ in EmployeeType.choices}
_UNSET = object()


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
    def prepare_create(self, requester, payload: dict) -> dict: ...

    @abstractmethod
    def create_prepared(self, fields: dict, *, is_active: bool = True): ...

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
        membership_repository: IUnitMembershipRepository,
        transaction_runner: ITransactionRunner,
    ):
        self._repo = user_repository
        self._policy = password_policy
        self._cpf = cpf_validator
        self._phone = phone_validator
        self._memberships = membership_repository
        self._transactions = transaction_runner

    def list_for(self, user, role=None, *, is_active=None, employee_type=None):
        if not is_admin(user):
            return [user]
        if role is not None and role not in _VALID_ROLES:
            raise BusinessRuleError(
                message=f"Filtro de perfil inválido: {role!r}.", field="role"
            )
        normalized_employee_type = None
        if employee_type is not None:
            normalized_employee_type = str(employee_type).upper()
            if normalized_employee_type not in _VALID_EMPLOYEE_TYPES:
                raise BusinessRuleError(
                    message=f"Filtro de tipo de funcionário inválido: {employee_type!r}.",
                    field="employee_type",
                )
        return self._repo.list_filtered(
            role=role,
            is_active=True if is_active is None else is_active,
            employee_type=normalized_employee_type,
            condominium_id=require_condominium_id(user),
        )

    def get_for(self, user, pk):
        instance = self._repo.get_by_id(pk)
        if not instance:
            raise NotFoundError("Nenhum usuário encontrado.")
        if not is_admin(user) and instance.id != user.id:
            raise NotFoundError("Nenhum usuário encontrado.")
        assert_same_condominium(user, instance.condominium_id)
        return instance

    def activate(self, user) -> None:
        self._repo.set_active(user, True)

    def hard_delete(self, user) -> None:
        self._repo.delete(user)

    def create(self, requester, payload: dict, *, is_active: bool = True):
        fields = self.prepare_create(requester, payload)
        return self._repo.create_user(**fields, is_active=is_active)

    def prepare_create(self, requester, payload: dict) -> dict:
        """Validate and normalize signup data without persisting."""
        is_anonymous = requester is None or not getattr(
            requester, "is_authenticated", False
        )
        if not is_anonymous and not getattr(requester, "is_staff", False):
            raise PermissionDeniedError(
                "Apenas usuários anônimos ou administradores podem criar contas."
            )

        data = dict(payload)
        role = data.pop("role", UserRole.RESIDENT)
        if role not in _VALID_ROLES:
            raise BusinessRuleError(
                message=f"Perfil inválido: {role!r}.", field="role"
            )
        if role != UserRole.RESIDENT and is_anonymous:
            raise PermissionDeniedError(
                "Apenas administradores podem criar usuários não residentes."
            )

        condominium_id = data.pop("condominium_id", None)
        condominium_code = data.pop("condominium_code", None)
        if is_anonymous:
            if not condominium_id:
                raise BusinessRuleError(
                    "condominium_id é obrigatório para cadastro anônimo.",
                    field="condominium_code",
                )
        elif is_platform_superuser(requester):
            if not condominium_id:
                raise BusinessRuleError(
                    "condominium_id é obrigatório ao criar usuários como superusuário.",
                    field="condominium_id",
                )
        else:
            condominium_id = require_condominium_id(requester)
            condominium_code = requester.condominium.code

        password = data.get("password", "")
        errors = self._policy.validate(password)
        if errors:
            raise BusinessRuleError(message=errors, field="password")

        username = data.get("username", "")
        if username:
            if not condominium_code:
                raise BusinessRuleError(
                    "condominium_code é obrigatório para validar o username.",
                    field="condominium_code",
                )
            if self._repo.exists_with_username(
                username, condominium_code=condominium_code
            ):
                raise BusinessRuleError(
                    message="Já existe um usuário com esse username.",
                    field="username",
                )
            username = build_tenant_username(condominium_code, username)

        email = (data.get("email") or "").lower().strip()
        if email and self._repo.exists_with_email(email):
            raise BusinessRuleError(
                message="Já existe uma conta com este e-mail.",
                field="email",
            )

        cpf = self._cpf.normalize(data.get("cpf", ""))
        cpf_error = self._cpf.validate(cpf)
        if cpf_error:
            raise BusinessRuleError(message=cpf_error, field="cpf")
        if self._repo.exists_with_cpf(cpf, condominium_id=condominium_id):
            raise BusinessRuleError(
                message="Já existe uma conta com este CPF.", field="cpf"
            )

        phone = self._phone.normalize(data.get("phone", ""))
        phone_error = self._phone.validate(phone)
        if phone_error:
            raise BusinessRuleError(message=phone_error, field="phone")

        employee_types = self._normalize_employee_types(
            role, data.pop("employee_types", None)
        )
        apartment = data.get("apartment", "") or ""
        block = data.get("block", "") or ""
        if role == UserRole.EMPLOYEE and (apartment or block):
            raise BusinessRuleError(
                "Funcionários não podem estar vinculados a um apartamento.",
                field="apartment",
            )

        return {
            "username": username,
            "password": password,
            "email": email,
            "full_name": data["full_name"],
            "birth_date": data["birth_date"],
            "cpf": cpf,
            "phone": phone,
            "apartment": apartment if role != UserRole.EMPLOYEE else "",
            "block": block if role != UserRole.EMPLOYEE else "",
            "photo": data.get("photo"),
            "role": role,
            "is_staff": role == UserRole.ADMIN,
            "employee_types": employee_types,
            "condominium_id": condominium_id,
        }

    def create_prepared(self, fields: dict, *, is_active: bool = True):
        """Persist fields previously returned by prepare_create."""
        email = (fields.get("email") or "").lower().strip()
        if email and self._repo.exists_with_email(email):
            raise BusinessRuleError(
                message="Já existe uma conta com este e-mail.",
                field="email",
            )
        cpf = fields.get("cpf") or ""
        condominium_id = fields.get("condominium_id")
        if cpf and self._repo.exists_with_cpf(cpf, condominium_id=condominium_id):
            raise BusinessRuleError(
                message="Já existe uma conta com este CPF.", field="cpf"
            )
        return self._repo.create_user(**dict(fields), is_active=is_active)

    def update(self, user, pk, payload):
        instance = self.get_for(user, pk)
        return self._update(user, instance, payload)

    def update_self(self, user, payload):
        if is_employee(user):
            raise PermissionDeniedError(
                "Funcionários não podem editar o próprio perfil."
            )
        return self._update(user, user, payload)

    def _update(self, requester, instance, payload):
        if not is_admin(requester):
            for field in _ADMIN_ONLY_PATCH_FIELDS & payload.keys():
                payload.pop(field)

        requested_is_active = payload.pop("is_active", _UNSET)
        if requested_is_active is not _UNSET:
            if not getattr(requester, "is_staff", False):
                raise PermissionDeniedError("Apenas administradores podem alterar o status da conta.")
            new_is_active = bool(requested_is_active)
            if requester.id == instance.id and not new_is_active:
                raise PermissionDeniedError("Administradores não podem desativar a própria conta.")

        if "role" in payload:
            new_role = payload["role"]
            if not getattr(requester, "is_staff", False):
                raise PermissionDeniedError("Apenas administradores podem alterar o perfil do usuário.")
            if new_role not in _VALID_ROLES:
                raise BusinessRuleError(
                    message=f"Perfil inválido: {new_role!r}.", field="role"
                )
            if (
                requester.id == instance.id
                and instance.role == UserRole.ADMIN
                and new_role != UserRole.ADMIN
            ):
                raise PermissionDeniedError(
                    "Administradores não podem rebaixar a si mesmos."
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
                    "Apenas administradores podem alterar os tipos de funcionário."
                )
            effective_role = payload.get("role", instance.role)
            payload["employee_types"] = self._normalize_employee_types(
                effective_role, payload["employee_types"]
            )

        if "email" in payload and payload["email"]:
            payload["email"] = payload["email"].lower().strip()
            if (
                payload["email"] != instance.email
                and self._repo.exists_with_email(payload["email"])
            ):
                raise BusinessRuleError(
                    message="Já existe uma conta com este e-mail.",
                    field="email",
                )

        if "username" in payload:
            username = payload["username"].strip()
            condominium_code = instance.condominium.code
            if self._repo.exists_with_username(
                username,
                condominium_code=condominium_code,
                exclude_id=instance.id,
            ):
                raise BusinessRuleError(
                    message="Já existe um usuário com esse username.",
                    field="username",
                )
            payload["username"] = build_tenant_username(
                condominium_code, username
            )

        if "cpf" in payload:
            cpf = self._cpf.normalize(payload["cpf"])
            cpf_error = self._cpf.validate(cpf)
            if cpf_error:
                raise BusinessRuleError(message=cpf_error, field="cpf")
            if self._repo.exists_with_cpf(
                cpf,
                condominium_id=instance.condominium_id,
                exclude_id=instance.id,
            ):
                raise BusinessRuleError(
                    message="Já existe uma conta com este CPF.",
                    field="cpf",
                )
            payload["cpf"] = cpf

        if "phone" in payload and payload["phone"]:
            phone = self._phone.normalize(payload["phone"])
            phone_error = self._phone.validate(phone)
            if phone_error:
                raise BusinessRuleError(message=phone_error, field="phone")
            payload["phone"] = phone

        if getattr(instance, "role", None) == UserRole.EMPLOYEE:
            payload.pop("apartment", None)
            payload.pop("block", None)

        if requested_is_active is not _UNSET:
            with self._transactions.atomic():
                if new_is_active:
                    self._repo.set_active(instance, True)
                else:
                    self._deactivate(instance)
                if payload:
                    return self._repo.update(instance, payload)
                return instance

        return self._repo.update(instance, payload)

    def delete(self, user, pk):
        if not is_admin(user):
            raise PermissionDeniedError("Apenas administradores podem desativar usuários.")
        instance = self.get_for(user, pk)
        if user.id == instance.id:
            raise PermissionDeniedError("Administradores não podem desativar a própria conta.")
        self._deactivate(instance)

    def _deactivate(self, instance) -> None:
        with self._transactions.atomic():
            memberships = list(
                self._memberships.list_active_for_user(instance.id)
            )
            for membership in memberships:
                if membership.role == UnitMembership.Role.OWNER:
                    replacement = (
                        self._memberships.get_oldest_active_replacement(
                            membership.unit_id, instance.id
                        )
                    )
                    if replacement:
                        self._memberships.update(
                            replacement,
                            {"role": UnitMembership.Role.OWNER},
                        )
                self._memberships.soft_leave(membership)
            self._repo.set_active(instance, False)

    @staticmethod
    def _normalize_employee_types(role: str, raw) -> list[str]:
        if role != UserRole.EMPLOYEE:
            return []
        if raw is None:
            raise BusinessRuleError(
                "Contas de funcionário exigem ao menos um tipo de funcionário.",
                field="employee_types",
            )
        if not isinstance(raw, (list, tuple)):
            raise BusinessRuleError(
                "employee_types deve ser uma lista.",
                field="employee_types",
            )
        normalized: list[str] = []
        for value in raw:
            upper = str(value).upper()
            if upper not in _VALID_EMPLOYEE_TYPES:
                raise BusinessRuleError(
                    message=f"Tipo de funcionário inválido: {value!r}.",
                    field="employee_types",
                )
            if upper not in normalized:
                normalized.append(upper)
        if not normalized:
            raise BusinessRuleError(
                "Contas de funcionário exigem ao menos um tipo de funcionário.",
                field="employee_types",
            )
        return normalized
