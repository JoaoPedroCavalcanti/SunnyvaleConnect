"""Authentication rules: produces a verdict for the LoginView to act on."""

from abc import ABC, abstractmethod

from households.repositories.membership_repository import IMembershipRepository
from users.repositories.user_repository import IUserRepository


KIND_OK = "ok"
KIND_INVALID = "invalid_credentials"
KIND_DISABLED = "account_disabled"
KIND_PENDING = "pending_household_approval"


class IAuthService(ABC):
    @abstractmethod
    def authenticate(self, email: str, password: str) -> dict: ...


class AuthService(IAuthService):
    def __init__(
        self,
        user_repository: IUserRepository,
        membership_repository: IMembershipRepository,
    ):
        self._users = user_repository
        self._memberships = membership_repository

    def authenticate(self, email: str, password: str):
        normalized_email = (email or "").lower().strip()
        user = self._users.get_by_email(normalized_email)
        if not user or not self._users.check_password(user, password or ""):
            return {"kind": KIND_INVALID}

        condominium = getattr(user, "condominium", None)
        if not condominium or not getattr(condominium, "is_active", True):
            return {"kind": KIND_INVALID}

        if user.is_active:
            return {
                "kind": KIND_OK,
                "user": user,
                "condominium": condominium,
            }

        pending = list(self._memberships.list_pending_for_user(user.id))
        if pending:
            membership = pending[0]
            household = membership.household
            return {
                "kind": KIND_PENDING,
                "user": user,
                "condominium": condominium,
                "household": {
                    "id": household.id,
                    "apartment": household.apartment,
                    "block": household.block,
                    "household_status": household.status,
                    "membership_status": membership.status,
                    "membership_role": membership.role,
                },
            }

        return {"kind": KIND_DISABLED, "user": user, "condominium": condominium}
