"""Permission-aware read service for membership decision history."""

from abc import ABC, abstractmethod

from shared.exceptions import (
    BusinessRuleError,
    NotFoundError,
    PermissionDeniedError,
)
from shared.tenant import assert_same_condominium, require_condominium_id
from units.models import UnitMembership, UnitMembershipDecision
from units.repositories.unit_membership_decision_repository import (
    IUnitMembershipDecisionRepository,
)
from units.repositories.unit_membership_repository import IUnitMembershipRepository
from units.repositories.unit_repository import IUnitRepository


class IUnitMembershipDecisionService(ABC):
    @abstractmethod
    def list_for_unit(self, user, unit_id: int): ...

    @abstractmethod
    def list_history(self, user, *, action: str | None = None): ...


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
            raise NotFoundError("Nenhuma unidade encontrada.")

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
                    "Apenas um proprietário ativo pode ver o histórico de decisões."
                )

        return list(self._repo.list_for_unit(unit.id))

    def list_history(self, user, *, action=None):
        """Condo-wide approve/reject history for condominium admins."""
        if not getattr(user, "is_staff", False):
            raise PermissionDeniedError(
                "Apenas administradores podem ver o histórico de decisões do condomínio."
            )
        normalized = None
        if action is not None and str(action).strip() != "":
            normalized = str(action).strip().upper()
            valid = {choice for choice, _ in UnitMembershipDecision.Action.choices}
            if normalized not in valid:
                raise BusinessRuleError(
                    message=(
                        f"Filtro de ação inválido: {action!r}. "
                        f"Use um de {sorted(valid)}."
                    ),
                    field="action",
                )
        condominium_id = require_condominium_id(user)
        return list(
            self._repo.list_for_condominium(
                condominium_id, action=normalized
            )
        )