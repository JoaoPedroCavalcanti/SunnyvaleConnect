"""Permission-aware read service for reservation decision history."""

from abc import ABC, abstractmethod

from reservations.models import ReservationDecision
from reservations.repositories.reservation_decision_repository import (
    IReservationDecisionRepository,
)
from shared.exceptions import BusinessRuleError, PermissionDeniedError
from shared.roles import is_admin
from shared.tenant import require_condominium_id


class IReservationDecisionService(ABC):
    @abstractmethod
    def list_history(
        self,
        user,
        *,
        action: str | None = None,
        location_id: int | None = None,
    ): ...


class ReservationDecisionService(IReservationDecisionService):
    def __init__(self, decision_repository: IReservationDecisionRepository):
        self._repo = decision_repository

    def list_history(self, user, *, action=None, location_id=None):
        if not is_admin(user):
            raise PermissionDeniedError(
                "Only staff can view the reservation decision history."
            )
        normalized_action = None
        if action is not None and str(action).strip() != "":
            normalized_action = str(action).strip().upper()
            valid = {
                choice for choice, _ in ReservationDecision.Action.choices
            }
            if normalized_action not in valid:
                raise BusinessRuleError(
                    message=(
                        f"Invalid action filter: {action!r}. "
                        f"Use one of {sorted(valid)}."
                    ),
                    field="action",
                )
        normalized_location = None
        if location_id is not None and str(location_id).strip() != "":
            try:
                normalized_location = int(location_id)
            except (TypeError, ValueError) as exc:
                raise BusinessRuleError(
                    message="location_id must be an integer.",
                    field="location_id",
                ) from exc
        condominium_id = require_condominium_id(user)
        return list(
            self._repo.list_for_condominium(
                condominium_id,
                action=normalized_action,
                location_id=normalized_location,
            )
        )
