"""Business rules for Household lifecycle (create / approve / reject / list)."""

from abc import ABC, abstractmethod

from households.models import Household, HouseholdMembership
from households.repositories.household_repository import IHouseholdRepository
from households.repositories.membership_repository import IMembershipRepository
from shared.exceptions import (
    BusinessRuleError,
    NotFoundError,
    PermissionDeniedError,
)
from shared.infrastructure.email_sender import IEmailSender
from users.repositories.user_repository import IUserRepository


class IHouseholdService(ABC):
    @abstractmethod
    def search_public(self, apartment: str | None, block: str | None): ...

    @abstractmethod
    def list_for(self, user, status: str | None = None): ...

    @abstractmethod
    def get_for(self, user, pk: int) -> Household: ...

    @abstractmethod
    def peek(self, pk: int) -> Household | None: ...

    @abstractmethod
    def request_create(
        self, user, apartment: str, block: str
    ) -> Household: ...

    @abstractmethod
    def approve(self, admin, pk: int) -> Household: ...

    @abstractmethod
    def reject(self, admin, pk: int, reason: str = "") -> None: ...


class HouseholdService(IHouseholdService):
    def __init__(
        self,
        household_repository: IHouseholdRepository,
        membership_repository: IMembershipRepository,
        user_repository: IUserRepository,
        email_sender: IEmailSender,
    ):
        self._repo = household_repository
        self._memberships = membership_repository
        self._users = user_repository
        self._email = email_sender

    # ---- queries -------------------------------------------------------- #
    def search_public(self, apartment, block):
        return self._repo.search(apartment=apartment, block=block or None)

    def list_for(self, user, status=None):
        if getattr(user, "is_staff", False):
            return list(self._repo.list_all(status=status))
        memberships = self._memberships.list_active_for_user(user.id)
        seen: dict[int, Household] = {}
        for m in memberships:
            household = m.household
            if status and household.status != status:
                continue
            seen[household.id] = household
        return list(seen.values())

    def get_for(self, user, pk):
        instance = self._repo.get_by_id(pk)
        if not instance:
            raise NotFoundError("No household matches the given query.")
        if getattr(user, "is_staff", False):
            return instance
        if not self._memberships.get_for_user_and_household(user.id, instance.id):
            raise NotFoundError("No household matches the given query.")
        return instance

    def peek(self, pk):
        """Permissionless lookup for orchestrators (e.g. signup pre-fill)."""
        return self._repo.get_by_id(pk)

    # ---- create flow ---------------------------------------------------- #
    def request_create(self, user, apartment, block):
        apartment = (apartment or "").strip()
        block = (block or "").strip()
        if not apartment:
            raise BusinessRuleError("apartment is required.", field="apartment")

        if self._repo.get_by_apartment_block(apartment, block):
            raise BusinessRuleError(
                "A household for this apartment/block already exists. "
                "Request to join it instead.",
                field="apartment",
            )

        household = self._repo.create(
            {
                "apartment": apartment,
                "block": block,
                "status": Household.Status.PENDING_ADMIN,
            }
        )

        self._memberships.create(
            {
                "household": household,
                "user": user,
                "role": HouseholdMembership.Role.HOLDER,
                "status": HouseholdMembership.Status.PENDING_ADMIN,
            }
        )

        for admin_email in self._users.list_admin_emails():
            self._email.send_household_creation_request(
                to_email=admin_email,
                requester_name=user.full_name or user.username,
                apartment=apartment,
                block=block,
            )

        return household

    # ---- approve / reject (admin) -------------------------------------- #
    def approve(self, admin, pk):
        if not getattr(admin, "is_staff", False):
            raise PermissionDeniedError("Only staff can approve households.")

        household = self._repo.get_by_id(pk)
        if not household:
            raise NotFoundError("No household matches the given query.")
        if household.status != Household.Status.PENDING_ADMIN:
            raise BusinessRuleError(
                "This household is not pending admin approval."
            )

        self._repo.update(household, {"status": Household.Status.ACTIVE})

        pending_memberships = [
            m
            for m in self._memberships.list_for_household(household.id)
            if m.status == HouseholdMembership.Status.PENDING_ADMIN
        ]
        for membership in pending_memberships:
            self._memberships.update(
                membership, {"status": HouseholdMembership.Status.ACTIVE}
            )
            self._users.set_active(membership.user, True)
            if membership.user.email:
                self._email.send_household_request_approved(
                    to_email=membership.user.email,
                    requester_name=(
                        membership.user.full_name or membership.user.username
                    ),
                    apartment=household.apartment,
                    block=household.block,
                )

        return household

    def reject(self, admin, pk, reason=""):
        if not getattr(admin, "is_staff", False):
            raise PermissionDeniedError("Only staff can reject households.")

        household = self._repo.get_by_id(pk)
        if not household:
            raise NotFoundError("No household matches the given query.")
        if household.status != Household.Status.PENDING_ADMIN:
            raise BusinessRuleError(
                "This household is not pending admin approval."
            )

        memberships = list(self._memberships.list_for_household(household.id))
        users_to_purge = []
        for membership in memberships:
            user = membership.user
            if user.email:
                self._email.send_household_request_rejected(
                    to_email=user.email,
                    requester_name=user.full_name or user.username,
                    apartment=household.apartment,
                    block=household.block,
                    reason=reason,
                )
            if not user.is_active and not self._memberships.list_active_for_user(
                user.id
            ):
                users_to_purge.append(user)

        self._repo.delete(household)
        for user in users_to_purge:
            self._users.delete(user)
