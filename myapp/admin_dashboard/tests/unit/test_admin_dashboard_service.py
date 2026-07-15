from types import SimpleNamespace

import pytest

from admin_dashboard.services.admin_dashboard_service import (
    AdminDashboardOverview,
    AdminDashboardService,
)
from reservations.models import Reservation
from shared.exceptions import PermissionDeniedError
from shared.test_doubles.fakes import FakeCache


pytestmark = pytest.mark.unit


class _CountRepository:
    def __init__(self, counts=None):
        self.counts = counts or {}

    def count_active(self, *, condominium_id=None):
        return self.counts.get("active", 0)

    def count_by_status(self, status, *, condominium_id):
        return self.counts.get(status, 0)

    def count_all(self, *, condominium_id):
        return self.counts.get("news", 0)


def _user(*, staff):
    return SimpleNamespace(
        is_staff=staff,
        condominium_id=1,
    )


def _service(*, active=0, approved=0, pending=0, news=0, cache=None):
    return AdminDashboardService(
        user_repository=_CountRepository({"active": active}),
        reservation_repository=_CountRepository(
            {
                Reservation.Status.APPROVED: approved,
                Reservation.Status.PENDING: pending,
            }
        ),
        news_repository=_CountRepository({"news": news}),
        cache=cache or FakeCache(),
    )


def test_admin_gets_generic_reservation_counts():
    result = _service(
        active=9,
        approved=4,
        pending=6,
        news=7,
    ).overview(_user(staff=True))

    assert result == AdminDashboardOverview(
        active_residents=9,
        total_reservations=4,
        pending_reservations=6,
        published_news=7,
    )


def test_non_admin_cannot_access_overview():
    with pytest.raises(PermissionDeniedError):
        _service().overview(_user(staff=False))


def test_overview_is_cached_for_one_hour():
    cache = FakeCache()
    service = _service(active=5, cache=cache)

    first = service.overview(_user(staff=True))
    second = service.overview(_user(staff=True))

    assert second is first
    assert cache.set_calls == [
        (
            f"{AdminDashboardService.CACHE_KEY_PREFIX}:1",
            first,
            3600,
        )
    ]
