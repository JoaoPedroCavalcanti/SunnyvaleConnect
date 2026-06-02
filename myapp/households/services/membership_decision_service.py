"""Read-only service for the membership decision audit log.

Writes happen inside ``MembershipService.approve`` / ``reject`` (they
already know the full context). This service exists only to expose the
log via a permission-aware listing endpoint.
"""

from abc import ABC, abstractmethod

from households.models import HouseholdMembership
from households.repositories.household_repository import IHouseholdRepository
from households.repositories.membership_decision_repository import (
    IMembershipDecisionRepository,
)
from households.repositories.membership_repository import IMembershipRepository
from shared.exceptions import NotFoundError, PermissionDeniedError


class IMembershipDecisionService(ABC):
    @abstractmethod
    def list_for_household(self, user, household_id: int): ...


class MembershipDecisionService(IMembershipDecisionService):
    def __init__(
        self,
        decision_repository: IMembershipDecisionRepository,
        membership_repository: IMembershipRepository,
        household_repository: IHouseholdRepository,
    ):
        self._repo = decision_repository
        self._memberships = membership_repository
        self._households = household_repository

    def list_for_household(self, user, household_id):
        """Audit log for a household. Scoped to active holders of the
        household or staff — residents don't get to see who rejected
        whom (sensitive)."""
        household = self._households.get_by_id(household_id)
        if not household:
            raise NotFoundError("No household matches the given query.")

        if not getattr(user, "is_staff", False):
            membership = self._memberships.get_for_user_and_household(
                user.id, household.id
            )
            if (
                not membership
                or membership.status != HouseholdMembership.Status.ACTIVE
                or membership.role != HouseholdMembership.Role.HOLDER
            ):
                raise PermissionDeniedError(
                    "Only an active holder of this household can view the "
                    "decision history."
                )

        return list(self._repo.list_for_household(household.id))
