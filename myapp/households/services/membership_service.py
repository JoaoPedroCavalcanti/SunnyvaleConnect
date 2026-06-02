"""Business rules for HouseholdMembership lifecycle.

Handles join requests, holder approvals, promotions, transfers and leaves.
"""

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


class IMembershipService(ABC):
    @abstractmethod
    def list_for_household(self, user, household_id: int): ...

    @abstractmethod
    def list_pending_approvals(self, user): ...

    @abstractmethod
    def request_join(self, user, household_id: int) -> HouseholdMembership: ...

    @abstractmethod
    def approve(self, holder, membership_id: int) -> HouseholdMembership: ...

    @abstractmethod
    def reject(
        self, holder, membership_id: int, reason: str = ""
    ) -> None: ...

    @abstractmethod
    def promote(self, holder, membership_id: int) -> HouseholdMembership: ...

    @abstractmethod
    def demote(self, holder, membership_id: int) -> HouseholdMembership: ...

    @abstractmethod
    def remove(self, holder, membership_id: int) -> None: ...

    @abstractmethod
    def leave(self, user, household_id: int) -> None: ...

    @abstractmethod
    def transfer(
        self, holder, household_id: int, to_user_id: int
    ) -> HouseholdMembership: ...


class MembershipService(IMembershipService):
    def __init__(
        self,
        membership_repository: IMembershipRepository,
        household_repository: IHouseholdRepository,
        user_repository: IUserRepository,
        email_sender: IEmailSender,
    ):
        self._repo = membership_repository
        self._households = household_repository
        self._users = user_repository
        self._email = email_sender

    # ---- queries ------------------------------------------------------- #
    def list_for_household(self, user, household_id):
        household = self._get_household_or_404(household_id)
        if not getattr(user, "is_staff", False):
            self._require_active_membership(user.id, household.id)
        return list(self._repo.list_for_household(household.id))

    def list_pending_approvals(self, user):
        """Returns the approvals the requesting user is allowed to act on.

        - Admin: every household awaiting admin approval (membership of the
          would-be HOLDER, status=PENDING_ADMIN).
        - Holder: residents waiting for holder approval, scoped to the
          households where the user is an active holder.
        - Anyone else: empty list (no error — front can render empty state).
        """
        if getattr(user, "is_staff", False):
            return list(self._repo.list_pending_admin())
        return list(self._repo.list_pending_holder_for_houses_of(user.id))

    # ---- join flow ----------------------------------------------------- #
    def request_join(self, user, household_id):
        household = self._get_household_or_404(household_id)
        if household.status != Household.Status.ACTIVE:
            raise BusinessRuleError(
                "This household is not open for new members."
            )

        existing = self._repo.get_for_user_and_household(user.id, household.id)
        if existing and existing.status != HouseholdMembership.Status.LEFT:
            raise BusinessRuleError(
                "You already have a pending or active membership for this household."
            )

        if self._repo.list_active_for_user(user.id):
            raise BusinessRuleError("User is already an active member of another household.")
        if self._repo.list_pending_for_user(user.id):
            raise BusinessRuleError("User already has a pending household request.")

        membership = self._repo.create(
            {
                "household": household,
                "user": user,
                "role": HouseholdMembership.Role.RESIDENT,
                "status": HouseholdMembership.Status.PENDING_HOLDER,
            }
        )

        for holder_m in self._repo.list_active_holders(household.id):
            holder = holder_m.user
            if holder.email:
                self._email.send_household_join_request(
                    to_email=holder.email,
                    holder_name=holder.full_name or holder.username,
                    requester_name=user.full_name or user.username,
                    apartment=household.apartment,
                    block=household.block,
                )

        return membership

    # ---- holder approvals --------------------------------------------- #
    def approve(self, holder, membership_id):
        membership = self._get_membership_or_404(membership_id)
        self._require_holder(holder, membership.household_id)

        if membership.status != HouseholdMembership.Status.PENDING_HOLDER:
            raise BusinessRuleError(
                "This membership is not pending holder approval."
            )

        self._repo.update(membership, {"status": HouseholdMembership.Status.ACTIVE})
        self._users.set_active(membership.user, True)

        if membership.user.email:
            self._email.send_household_request_approved(
                to_email=membership.user.email,
                requester_name=(
                    membership.user.full_name or membership.user.username
                ),
                apartment=membership.household.apartment,
                block=membership.household.block,
            )
        return membership

    def reject(self, holder, membership_id, reason=""):
        membership = self._get_membership_or_404(membership_id)
        self._require_holder(holder, membership.household_id)

        if membership.status != HouseholdMembership.Status.PENDING_HOLDER:
            raise BusinessRuleError(
                "This membership is not pending holder approval."
            )

        user = membership.user
        household = membership.household
        if user.email:
            self._email.send_household_request_rejected(
                to_email=user.email,
                requester_name=user.full_name or user.username,
                apartment=household.apartment,
                block=household.block,
                reason=reason,
            )

        self._repo.delete(membership)
        if (
            not user.is_active
            and not self._repo.list_active_for_user(user.id)
            and not self._repo.list_pending_for_user(user.id)
        ):
            self._users.delete(user)

    # ---- promote / demote --------------------------------------------- #
    def promote(self, holder, membership_id):
        membership = self._get_membership_or_404(membership_id)
        self._require_holder(holder, membership.household_id)
        self._require_active(membership)

        if membership.role == HouseholdMembership.Role.HOLDER:
            raise BusinessRuleError("Member is already a holder.")

        return self._repo.update(
            membership, {"role": HouseholdMembership.Role.HOLDER}
        )

    def demote(self, holder, membership_id):
        membership = self._get_membership_or_404(membership_id)
        self._require_holder(holder, membership.household_id)
        self._require_active(membership)

        if membership.role != HouseholdMembership.Role.HOLDER:
            raise BusinessRuleError("Member is not a holder.")

        active_holders = list(self._repo.list_active_holders(membership.household_id))
        if len(active_holders) <= 1:
            raise BusinessRuleError(
                "Cannot demote the last holder. Promote another member first."
            )

        return self._repo.update(
            membership, {"role": HouseholdMembership.Role.RESIDENT}
        )

    # ---- remove / leave ----------------------------------------------- #
    def remove(self, holder, membership_id):
        membership = self._get_membership_or_404(membership_id)
        self._require_holder(holder, membership.household_id)
        self._require_active(membership)

        if membership.user_id == holder.id:
            raise BusinessRuleError(
                "Use /leave to remove yourself; /remove is for other members."
            )
        if membership.role == HouseholdMembership.Role.HOLDER:
            raise BusinessRuleError(
                "Cannot remove another holder directly; demote them first."
            )

        self._repo.soft_leave(membership)

    def leave(self, user, household_id):
        household = self._get_household_or_404(household_id)
        membership = self._repo.get_for_user_and_household(user.id, household.id)
        if not membership or membership.status != HouseholdMembership.Status.ACTIVE:
            raise NotFoundError("You are not a member of this household.")

        if membership.role == HouseholdMembership.Role.HOLDER:
            other_holders = [
                h
                for h in self._repo.list_active_holders(household.id)
                if h.id != membership.id
            ]
            other_members = [
                m
                for m in self._repo.list_active_for_household(household.id)
                if m.id != membership.id
            ]
            if not other_holders and other_members:
                raise BusinessRuleError(
                    "You are the last holder but there are other members. "
                    "Promote another member to holder before leaving."
                )

        self._repo.soft_leave(membership)

        remaining = list(self._repo.list_active_for_household(household.id))
        if not remaining:
            self._households.update(
                household, {"status": Household.Status.ARCHIVED}
            )

    # ---- transfer ----------------------------------------------------- #
    def transfer(self, holder, household_id, to_user_id):
        household = self._get_household_or_404(household_id)
        self._require_holder(holder, household.id)

        if to_user_id == holder.id:
            raise BusinessRuleError("You are already a holder.")

        target = self._repo.get_for_user_and_household(to_user_id, household.id)
        if not target or target.status != HouseholdMembership.Status.ACTIVE:
            raise BusinessRuleError("Target user is not an active member.")
        if target.role == HouseholdMembership.Role.HOLDER:
            raise BusinessRuleError("Target user is already a holder.")

        return self._repo.update(target, {"role": HouseholdMembership.Role.HOLDER})

    # ---- internal helpers --------------------------------------------- #
    def _get_household_or_404(self, household_id) -> Household:
        household = self._households.get_by_id(household_id)
        if not household:
            raise NotFoundError("No household matches the given query.")
        return household

    def _get_membership_or_404(self, pk) -> HouseholdMembership:
        membership = self._repo.get_by_id(pk)
        if not membership:
            raise NotFoundError("No membership matches the given query.")
        return membership

    def _require_holder(self, user, household_id) -> None:
        if getattr(user, "is_staff", False):
            return
        holder = self._repo.get_for_user_and_household(user.id, household_id)
        if (
            not holder
            or holder.status != HouseholdMembership.Status.ACTIVE
            or holder.role != HouseholdMembership.Role.HOLDER
        ):
            raise PermissionDeniedError("Only an active holder can perform this action.")

    def _require_active_membership(self, user_id, household_id) -> None:
        membership = self._repo.get_for_user_and_household(user_id, household_id)
        if (
            not membership
            or membership.status != HouseholdMembership.Status.ACTIVE
        ):
            raise PermissionDeniedError(
                "You must be an active member of this household."
            )

    def _require_active(self, membership) -> None:
        if membership.status != HouseholdMembership.Status.ACTIVE:
            raise BusinessRuleError("Membership is not active.")
