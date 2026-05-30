"""Business rules for users."""

from abc import ABC, abstractmethod

from shared.exceptions import BusinessRuleError, NotFoundError, PermissionDeniedError
from shared.infrastructure.password_policy import IPasswordPolicy
from users.repositories.user_repository import IUserRepository


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
    ):
        self._repo = user_repository
        self._policy = password_policy

    def list_for(self, user):
        if user.is_staff:
            return self._repo.list_all()
        # regular user sees only itself
        return [user]

    def get_for(self, user, pk):
        instance = self._repo.get_by_id(pk)
        if not instance:
            raise NotFoundError("No user matches the given query.")
        if not user.is_staff and instance.id != user.id:
            # mimic the previous queryset filtering: not in scope -> 404
            raise NotFoundError("No user matches the given query.")
        return instance

    def create(self, requester, payload: dict):
        # Only anonymous users or staff can create accounts.
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

        email = payload.get("email")
        if email and self._repo.exists_with_email(email):
            raise BusinessRuleError(
                message="An account with this email address already exists.",
                field="email",
            )

        return self._repo.create_user(
            username=payload["username"],
            password=password,
            first_name=payload["first_name"],
            last_name=payload["last_name"],
            email=email,
        )

    def update(self, user, pk, payload):
        instance = self.get_for(user, pk)
        return self._update(instance, payload)

    def update_self(self, user, payload):
        return self._update(user, payload)

    def _update(self, instance, payload):
        if "password" in payload:
            errors = self._policy.validate(payload["password"])
            if errors:
                raise BusinessRuleError(message=errors, field="password")
        if "email" in payload and payload["email"]:
            if (
                payload["email"] != instance.email
                and self._repo.exists_with_email(payload["email"])
            ):
                raise BusinessRuleError(
                    message="An account with this email address already exists.",
                    field="email",
                )
        return self._repo.update(instance, payload)

    def delete(self, user, pk):
        instance = self.get_for(user, pk)
        self._repo.delete(instance)
