"""Business rules for Household lifecycle (create / approve / reject / list)."""

from abc import ABC, abstractmethod

from condominiums.repositories.condominium_repository import ICondominiumRepository
from households.models import Household, HouseholdMembership
from households.repositories.household_repository import IHouseholdRepository
from households.repositories.membership_repository import IMembershipRepository
from shared.exceptions import (
    BusinessRuleError,
    NotFoundError,
    PermissionDeniedError,
)
from shared.infrastructure.email_sender import IEmailSender
from shared.infrastructure.transactions import ITransactionRunner
from shared.tenant import assert_same_condominium, require_condominium_id
from users.repositories.user_repository import IUserRepository


class IHouseholdService(ABC):
    @abstractmethod
    def search_public(self, condominium_code: str, apartment: str | None, block: str | None): ...

    @abstractmethod
    def list_for(self, user, status: str | None = None): ...

    @abstractmethod
    def list_for_with_members(
        self, user, status: str | None = None
    ) -> list[dict]: ...

    @abstractmethod
    def get_for(self, user, pk: int) -> Household: ...

    @abstractmethod
    def peek(self, pk: int, *, condominium_id: int) -> Household | None: ...

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
        transaction_runner: ITransactionRunner,
        condominium_repository: ICondominiumRepository,
    ):
        self._repo = household_repository
        self._memberships = membership_repository
        self._users = user_repository
        self._email = email_sender
        self._tx = transaction_runner
        self._condominiums = condominium_repository

    # ---- queries -------------------------------------------------------- #
    def search_public(self, condominium_code: str, apartment, block):
        condominium = self._condominiums.get_by_code(condominium_code)
        if not condominium or not condominium.is_active:
            raise NotFoundError("Invalid or inactive condominium code.")
        return self._repo.search(
            apartment=apartment,
            block=block or None,
            condominium_id=condominium.id,
        )

    def list_for(self, user, status=None):
        condominium_id = require_condominium_id(user)
        if getattr(user, "is_staff", False):
            return list(
                self._repo.list_all(status=status, condominium_id=condominium_id)
            )
        memberships = self._memberships.list_active_for_user(user.id)
        seen: dict[int, Household] = {}
        for m in memberships:
            household = m.household
            if status and household.status != status:
                continue
            seen[household.id] = household
        return list(seen.values())

    def list_for_with_members(self, user, status=None):
        """Same scope as ``list_for`` but each item carries active members.

        Returns a list of ``{"household": Household, "members": list}``.
        Members are loaded in one batched query to avoid N+1 on the admin
        listing.
        """
        households = list(self.list_for(user, status=status))
        if not households:
            return []
        memberships = self._memberships.list_active_for_households(
            [h.id for h in households]
        )
        grouped: dict[int, list] = {h.id: [] for h in households}
        for m in memberships:
            grouped.setdefault(m.household_id, []).append(m)
        return [
            {"household": h, "members": grouped.get(h.id, [])}
            for h in households
        ]

    def get_for(self, user, pk):
        instance = self._repo.get_by_id(pk)
        if not instance:
            raise NotFoundError("No household matches the given query.")
        assert_same_condominium(user, instance.condominium_id)
        if getattr(user, "is_staff", False):
            return instance
        if not self._memberships.get_for_user_and_household(user.id, instance.id):
            raise NotFoundError("No household matches the given query.")
        return instance

    def peek(self, pk, *, condominium_id: int):
        """Permissionless lookup for orchestrators (e.g. signup pre-fill)."""
        instance = self._repo.get_by_id(pk)
        if not instance or instance.condominium_id != condominium_id:
            return None
        return instance

    # ---- create flow ---------------------------------------------------- #
    def request_create(self, user, apartment, block):
        condominium_id = require_condominium_id(user)
        apartment = (apartment or "").strip()
        block = (block or "").strip()
        if not apartment:
            raise BusinessRuleError("apartment is required.", field="apartment")

        if self._repo.get_by_apartment_block(
            apartment, block, condominium_id=condominium_id
        ):
            raise BusinessRuleError(
                "A household for this apartment/block already exists. "
                "Request to join it instead.",
                field="apartment",
            )

        with self._tx.atomic():
            household = self._repo.create(
                {
                    "apartment": apartment,
                    "block": block,
                    "status": Household.Status.PENDING_ADMIN,
                    "condominium_id": condominium_id,
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

        # Notify admins after the DB transaction is committed: a mail blip
        # must not roll back the household creation.
        requester_name = user.full_name or user.username
        for admin_email in self._users.list_admin_emails(
            condominium_id=condominium_id
        ):
            self._email.send_household_creation_request(
                to_email=admin_email,
                requester_name=requester_name,
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
        assert_same_condominium(admin, household.condominium_id)
        if household.status != Household.Status.PENDING_ADMIN:
            raise BusinessRuleError(
                "This household is not pending admin approval."
            )

        # Snapshot recipients inside the atomic block so we don't email
        # anyone if the multi-row update rolls back halfway.
        recipients: list[tuple[str, str]] = []
        with self._tx.atomic():
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
                    recipients.append(
                        (
                            membership.user.email,
                            membership.user.full_name
                            or membership.user.username,
                        )
                    )

        for to_email, requester_name in recipients:
            self._email.send_household_request_approved(
                to_email=to_email,
                requester_name=requester_name,
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
        assert_same_condominium(admin, household.condominium_id)
        if household.status != Household.Status.PENDING_ADMIN:
            raise BusinessRuleError(
                "This household is not pending admin approval."
            )

        apartment = household.apartment
        block = household.block

        recipients: list[tuple[str, str]] = []
        with self._tx.atomic():
            memberships = list(self._memberships.list_for_household(household.id))
            users_to_purge = []
            for membership in memberships:
                user = membership.user
                if user.email:
                    recipients.append(
                        (user.email, user.full_name or user.username)
                    )
                if (
                    not user.is_active
                    and not self._memberships.list_active_for_user(user.id)
                ):
                    users_to_purge.append(user)

            self._repo.delete(household)
            for user in users_to_purge:
                self._users.delete(user)

        for to_email, requester_name in recipients:
            self._email.send_household_request_rejected(
                to_email=to_email,
                requester_name=requester_name,
                apartment=apartment,
                block=block,
                reason=reason,
            )
