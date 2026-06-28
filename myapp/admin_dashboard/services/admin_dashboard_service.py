"""Aggregator service that powers the admin home overview.

Fans out to existing repositories and rolls them up into a single
payload so the front does one HTTP call instead of four. The result
is cached for 1 hour: counters can lag a bit but the front gets a
near-instant response and we save five COUNT(*) per request.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from bbq_reservations.models import BBQReservationModel
from bbq_reservations.repositories.bbq_repository import IBBQRepository
from hall_reservations.models import HallReservationModel
from hall_reservations.repositories.hall_repository import IHallRepository
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
    pending_bbq_reservations: int
    pending_hall_reservations: int
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
        bbq_repository: IBBQRepository,
        hall_repository: IHallRepository,
        news_repository: ISunnyValeNewsRepository,
        cache: ICache,
    ):
        self._users = user_repository
        self._bbq = bbq_repository
        self._hall = hall_repository
        self._news = news_repository
        self._cache = cache

    @staticmethod
    def _require_admin(user) -> None:
        if not getattr(user, "is_staff", False):
            raise PermissionDeniedError(
                "Only staff users can access the admin dashboard."
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
        approved = (
            self._bbq.count_by_status(
                BBQReservationModel.Status.APPROVED,
                condominium_id=condominium_id,
            )
            + self._hall.count_by_status(
                HallReservationModel.Status.APPROVED,
                condominium_id=condominium_id,
            )
        )
        pending_bbq = self._bbq.count_by_status(
            BBQReservationModel.Status.PENDING,
            condominium_id=condominium_id,
        )
        pending_hall = self._hall.count_by_status(
            HallReservationModel.Status.PENDING,
            condominium_id=condominium_id,
        )
        return AdminDashboardOverview(
            active_residents=self._users.count_active(
                condominium_id=condominium_id
            ),
            total_reservations=approved,
            pending_reservations=pending_bbq + pending_hall,
            pending_bbq_reservations=pending_bbq,
            pending_hall_reservations=pending_hall,
            published_news=self._news.count_all(condominium_id=condominium_id),
        )
