"""Dumb repository for MembershipDecision. Pure ORM access."""

from abc import ABC, abstractmethod
from typing import Iterable

from households.models import MembershipDecision


class IMembershipDecisionRepository(ABC):
    @abstractmethod
    def record(self, data: dict) -> MembershipDecision: ...

    @abstractmethod
    def list_for_household(
        self, household_id: int
    ) -> Iterable[MembershipDecision]: ...


class DjangoMembershipDecisionRepository(IMembershipDecisionRepository):
    def record(self, data):
        return MembershipDecision.objects.create(**data)

    def list_for_household(self, household_id):
        return MembershipDecision.objects.filter(
            household_id=household_id
        ).order_by("-created_at", "-id")
