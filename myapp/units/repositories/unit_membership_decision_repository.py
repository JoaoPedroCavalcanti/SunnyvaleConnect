"""Dumb repository for UnitMembershipDecision. Pure ORM access."""

from abc import ABC, abstractmethod
from typing import Iterable

from units.models import UnitMembershipDecision


class IUnitMembershipDecisionRepository(ABC):
    @abstractmethod
    def record(self, data: dict) -> UnitMembershipDecision: ...

    @abstractmethod
    def list_for_unit(
        self, unit_id: int
    ) -> Iterable[UnitMembershipDecision]: ...


class DjangoUnitMembershipDecisionRepository(
    IUnitMembershipDecisionRepository
):
    def record(self, data):
        return UnitMembershipDecision.objects.create(**data)

    def list_for_unit(self, unit_id):
        return UnitMembershipDecision.objects.filter(unit_id=unit_id).order_by(
            "-created_at", "-id"
        )
