"""Dumb repository for ReservationDecision. Pure ORM access."""

from abc import ABC, abstractmethod
from typing import Iterable

from reservations.models import ReservationDecision


class IReservationDecisionRepository(ABC):
    @abstractmethod
    def record(self, data: dict) -> ReservationDecision: ...

    @abstractmethod
    def list_for_condominium(
        self,
        condominium_id: int,
        *,
        action: str | None = None,
        location_id: int | None = None,
    ) -> Iterable[ReservationDecision]: ...


class DjangoReservationDecisionRepository(IReservationDecisionRepository):
    def record(self, data):
        return ReservationDecision.objects.create(**data)

    def list_for_condominium(
        self, condominium_id, *, action=None, location_id=None
    ):
        qs = ReservationDecision.objects.filter(
            condominium_id=condominium_id
        )
        if action is not None:
            qs = qs.filter(action=action)
        if location_id is not None:
            qs = qs.filter(location_id=location_id)
        return qs.select_related(
            "reservation",
            "location",
            "unit",
            "actor",
            "target",
        ).order_by("-created_at", "-id")
