"""Authentication rules: produces a verdict for the LoginView to act on."""

from abc import ABC, abstractmethod

from units.models import UnitMembership
from units.repositories.unit_membership_repository import IUnitMembershipRepository
from users.repositories.user_repository import IUserRepository


KIND_OK = "ok"
KIND_INVALID = "invalid_credentials"
KIND_DISABLED = "account_disabled"
KIND_PENDING = "pending_unit_approval"
KIND_PENDING_EMAIL = "pending_email_verification"


class IAuthService(ABC):
    @abstractmethod
    def authenticate(self, email: str, password: str) -> dict: ...


class AuthService(IAuthService):
    def __init__(
        self,
        user_repository: IUserRepository,
        membership_repository: IUnitMembershipRepository,
    ):
        self._users = user_repository
        self._memberships = membership_repository

    def authenticate(self, email: str, password: str):
        normalized_email = (email or "").lower().strip()
        user = self._users.get_by_email(normalized_email)
        if not user or not self._users.check_password(user, password or ""):
            return {"kind": KIND_INVALID}

        condominium = getattr(user, "condominium", None)
        # Platform superusers are not tied to a condominium; condo accounts
        # still require an active tenant.
        if not getattr(user, "is_superuser", False):
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
            unit = membership.unit
            kind = (
                KIND_PENDING_EMAIL
                if membership.status == UnitMembership.Status.PENDING_EMAIL
                else KIND_PENDING
            )
            return {
                "kind": kind,
                "user": user,
                "condominium": condominium,
                "unit": {
                    "id": unit.id,
                    "display_name": unit.display_name(),
                    "unit_status": unit.status,
                    "membership_status": membership.status,
                    "membership_role": membership.role,
                },
            }

        return {"kind": KIND_DISABLED, "user": user, "condominium": condominium}
