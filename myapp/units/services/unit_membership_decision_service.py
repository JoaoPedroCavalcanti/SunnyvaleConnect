"""Permission-aware read service for membership decision history."""

from abc import ABC, abstractmethod

from shared.exceptions import NotFoundError, PermissionDeniedError
from shared.tenant import assert_same_condominium
from units.models import UnitMembership
from units.repositories.unit_membership_decision_repository import (
    IUnitMembershipDecisionRepository,
)
from units.repositories.unit_membership_repository import IUnitMembershipRepository
from units.repositories.unit_repository import IUnitRepository


class IUnitMembershipDecisionService(ABC):
    @abstractmethod
    def list_for_unit(self, user, unit_id: int): ...


class UnitMembershipDecisionService(IUnitMembershipDecisionService):
    def __init__(
        self,
        decision_repository: IUnitMembershipDecisionRepository,
        membership_repository: IUnitMembershipRepository,
        unit_repository: IUnitRepository,
    ):
        self._repo = decision_repository
        self._memberships = membership_repository
        self._units = unit_repository

    def list_for_unit(self, user, unit_id):
        unit = self._units.get_by_id(unit_id)
        if not unit:
            raise NotFoundError("No unit matches the given query.")

        assert_same_condominium(user, unit.condominium_id)
        if not getattr(user, "is_staff", False):
            membership = self._memberships.get_for_user_and_unit(
                user.id, unit.id
            )
            if (
                not membership
                or membership.status != UnitMembership.Status.ACTIVE
                or membership.role != UnitMembership.Role.OWNER
            ):
                raise PermissionDeniedError(
                    "Only an active owner can view the decision history."
                )

        return list(self._repo.list_for_unit(unit.id))
