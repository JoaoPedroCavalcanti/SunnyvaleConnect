"""Aggregator service that powers the admin home overview.

Fans out to existing repositories and rolls them up into a single
payload so the front does one HTTP call instead of four. The result
is cached for 1 hour: counters can lag a bit but the front gets a
near-instant response and we save five COUNT(*) per request.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from reservations.models import Reservation
from reservations.repositories.reservation_repository import (
    IReservationRepository,
)
from shared.exceptions import PermissionDeniedError
from shared.infrastructure.cache import ICache
from shared.tenant import require_condominium_id
from sunny_vale_news.repositories.sunny_vale_news_repository import (
    ISunnyValeNewsRepository,
)
from users.repositories.user_repository import IUserRepository


_CACHE_KEY_PREFIX = "admin_dashboard:overview"
_CACHE_TTL_SECONDS = 60 * 60  # 1 hour


@dataclass(frozen=True)
class AdminDashboardOverview:
    active_residents: int
    total_reservations: int
    pending_reservations: int
    published_news: int


class IAdminDashboardService(ABC):
    @abstractmethod
    def overview(self, user) -> AdminDashboardOverview: ...


class AdminDashboardService(IAdminDashboardService):
    CACHE_KEY_PREFIX = _CACHE_KEY_PREFIX
    CACHE_TTL_SECONDS = _CACHE_TTL_SECONDS

    def __init__(
        self,
        user_repository: IUserRepository,
        reservation_repository: IReservationRepository,
        news_repository: ISunnyValeNewsRepository,
        cache: ICache,
    ):
        self._users = user_repository
        self._reservations = reservation_repository
        self._news = news_repository
        self._cache = cache

    @staticmethod
    def _require_admin(user) -> None:
        if not getattr(user, "is_staff", False):
            raise PermissionDeniedError(
                "Apenas administradores podem acessar o painel administrativo."
            )

    def overview(self, user) -> AdminDashboardOverview:
        # Permission check always runs (never served from cache) so a
        # non-admin can not get the payload just because an admin warmed
        # the cache earlier.
        self._require_admin(user)

        condominium_id = require_condominium_id(user)
        cache_key = f"{self.CACHE_KEY_PREFIX}:{condominium_id}"
        cached = self._cache.get(cache_key)
        if isinstance(cached, AdminDashboardOverview):
            return cached

        result = self._compute(condominium_id)
        self._cache.set(cache_key, result, self.CACHE_TTL_SECONDS)
        return result

    def _compute(self, condominium_id: int) -> AdminDashboardOverview:
        approved = self._reservations.count_by_status(
            Reservation.Status.APPROVED,
            condominium_id=condominium_id,
        )
        pending = self._reservations.count_by_status(
            Reservation.Status.PENDING,
            condominium_id=condominium_id,
        )
        return AdminDashboardOverview(
            active_residents=self._users.count_active(
                condominium_id=condominium_id
            ),
            total_reservations=approved,
            pending_reservations=pending,
            published_news=self._news.count_all(condominium_id=condominium_id),
        )
