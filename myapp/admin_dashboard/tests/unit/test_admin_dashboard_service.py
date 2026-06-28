"""Unit tests for AdminDashboardService with in-memory fakes."""

from types import SimpleNamespace

import pytest

from admin_dashboard.services.admin_dashboard_service import (
    AdminDashboardOverview,
    AdminDashboardService,
)
from bbq_reservations.models import BBQReservationModel
from bbq_reservations.repositories.bbq_repository import IBBQRepository
from hall_reservations.models import HallReservationModel
from hall_reservations.repositories.hall_repository import IHallRepository
from shared.exceptions import PermissionDeniedError
from shared.test_doubles.fakes import FakeCache
from sunny_vale_news.repositories.sunny_vale_news_repository import (
    ISunnyValeNewsRepository,
)
from users.repositories.user_repository import IUserRepository


pytestmark = pytest.mark.unit

TEST_CONDOMINIUM_ID = 1


class _CountUserRepo(IUserRepository):
    """Tiny fake: only ``count_active`` matters here. Other ABC methods raise."""

    def __init__(self, active: int):
        self._active = active

    def count_active(self, *, condominium_id=None):
        return self._active

    # rest of the ABC is unused by AdminDashboardService
    def list_all(self, *, condominium_id=None):  # pragma: no cover
        raise NotImplementedError

    def list_by_role(self, role, *, condominium_id=None):  # pragma: no cover
        raise NotImplementedError

    def list_filtered(self, **kwargs):  # pragma: no cover
        raise NotImplementedError

    def get_by_id(self, pk):  # pragma: no cover
        raise NotImplementedError

    def exists_with_email(self, email):  # pragma: no cover
        raise NotImplementedError

    def exists_with_username(self, username, *, condominium_code):  # pragma: no cover
        raise NotImplementedError

    def exists_with_cpf(self, cpf, *, condominium_id):  # pragma: no cover
        raise NotImplementedError

    def create_user(self, **fields):  # pragma: no cover
        raise NotImplementedError

    def update(self, instance, data):  # pragma: no cover
        raise NotImplementedError

    def delete(self, instance):  # pragma: no cover
        raise NotImplementedError

    def set_active(self, instance, value):  # pragma: no cover
        raise NotImplementedError

    def list_admin_emails(self, *, condominium_id):  # pragma: no cover
        raise NotImplementedError

    def get_by_email(self, email):  # pragma: no cover
        raise NotImplementedError

    def get_by_username(self, username, *, condominium_code=None):  # pragma: no cover
        raise NotImplementedError

    def check_password(self, instance, raw_password):  # pragma: no cover
        raise NotImplementedError


class _CountBBQRepo(IBBQRepository):
    def __init__(self, by_status: dict[str, int]):
        self._by_status = by_status

    def count_by_status(self, status=None, *, condominium_id):
        if status is None:
            return sum(self._by_status.values())
        return self._by_status.get(status, 0)

    def list_all(self, status=None, *, condominium_id):  # pragma: no cover
        raise NotImplementedError

    def get_by_id(self, pk):  # pragma: no cover
        raise NotImplementedError

    def list_for_date(self, reservation_date, *, condominium_id):  # pragma: no cover
        raise NotImplementedError

    def latest_date_for_household(self, household_id):  # pragma: no cover
        raise NotImplementedError

    def create(self, data):  # pragma: no cover
        raise NotImplementedError

    def update(self, instance, data):  # pragma: no cover
        raise NotImplementedError

    def delete(self, instance):  # pragma: no cover
        raise NotImplementedError


class _CountHallRepo(IHallRepository):
    def __init__(self, by_status: dict[str, int]):
        self._by_status = by_status

    def count_by_status(self, status=None, *, condominium_id):
        if status is None:
            return sum(self._by_status.values())
        return self._by_status.get(status, 0)

    def list_all(self, status=None, *, condominium_id):  # pragma: no cover
        raise NotImplementedError

    def get_by_id(self, pk):  # pragma: no cover
        raise NotImplementedError

    def list_for_date(self, reservation_date, *, condominium_id):  # pragma: no cover
        raise NotImplementedError

    def latest_date_for_household(self, household_id):  # pragma: no cover
        raise NotImplementedError

    def create(self, data):  # pragma: no cover
        raise NotImplementedError

    def update(self, instance, data):  # pragma: no cover
        raise NotImplementedError

    def delete(self, instance):  # pragma: no cover
        raise NotImplementedError


class _CountNewsRepo(ISunnyValeNewsRepository):
    def __init__(self, total: int):
        self._total = total

    def count_all(self, *, condominium_id):
        return self._total

    def list_all(self, *, condominium_id):  # pragma: no cover
        raise NotImplementedError

    def list_by_kind(self, kind, *, condominium_id):  # pragma: no cover
        raise NotImplementedError

    def get_by_id(self, news_id):  # pragma: no cover
        raise NotImplementedError

    def create(self, data):  # pragma: no cover
        raise NotImplementedError

    def update(self, instance, data):  # pragma: no cover
        raise NotImplementedError

    def delete(self, instance):  # pragma: no cover
        raise NotImplementedError


def _admin():
    return SimpleNamespace(
        id=1, is_staff=True, role="ADMIN", condominium_id=TEST_CONDOMINIUM_ID
    )


def _resident():
    return SimpleNamespace(
        id=2, is_staff=False, role="RESIDENT", condominium_id=TEST_CONDOMINIUM_ID
    )


def _service(
    *,
    active=0,
    bbq=None,
    hall=None,
    news=0,
    cache=None,
):
    return AdminDashboardService(
        user_repository=_CountUserRepo(active),
        bbq_repository=_CountBBQRepo(bbq or {}),
        hall_repository=_CountHallRepo(hall or {}),
        news_repository=_CountNewsRepo(news),
        cache=cache or FakeCache(),
    )


def test_admin_gets_overview_with_aggregated_counts():
    svc = _service(
        active=9,
        bbq={
            BBQReservationModel.Status.APPROVED: 1,
            BBQReservationModel.Status.PENDING: 2,
            BBQReservationModel.Status.REJECTED: 5,
        },
        hall={
            HallReservationModel.Status.APPROVED: 3,
            HallReservationModel.Status.PENDING: 4,
        },
        news=7,
    )

    result = svc.overview(_admin())

    assert result.active_residents == 9
    # APPROVED only: 1 (BBQ) + 3 (Hall) = 4
    assert result.total_reservations == 4
    # PENDING only: 2 (BBQ) + 4 (Hall) = 6
    assert result.pending_reservations == 6
    assert result.pending_bbq_reservations == 2
    assert result.pending_hall_reservations == 4
    assert result.published_news == 7


def test_overview_zeros_when_repos_empty():
    result = _service().overview(_admin())
    assert result.active_residents == 0
    assert result.total_reservations == 0
    assert result.pending_reservations == 0
    assert result.pending_bbq_reservations == 0
    assert result.pending_hall_reservations == 0
    assert result.published_news == 0


def test_non_admin_cannot_access_overview():
    with pytest.raises(PermissionDeniedError):
        _service().overview(_resident())


def test_rejected_reservations_do_not_count_as_total():
    svc = _service(
        bbq={BBQReservationModel.Status.REJECTED: 99},
        hall={HallReservationModel.Status.REJECTED: 99},
    )
    result = svc.overview(_admin())
    assert result.total_reservations == 0
    assert result.pending_reservations == 0
    assert result.pending_bbq_reservations == 0
    assert result.pending_hall_reservations == 0


def test_overview_is_cached_with_one_hour_ttl():
    cache = FakeCache()
    svc = _service(active=5, news=2, cache=cache)
    svc.overview(_admin())
    assert cache.set_calls == [
        (
            f"{AdminDashboardService.CACHE_KEY_PREFIX}:1",
            cache.store[f"{AdminDashboardService.CACHE_KEY_PREFIX}:1"],
            3600,
        )
    ]


def test_second_call_hits_cache_and_skips_repos():
    cache = FakeCache()
    cache.store[f"{AdminDashboardService.CACHE_KEY_PREFIX}:1"] = AdminDashboardOverview(
        active_residents=42,
        total_reservations=7,
        pending_reservations=3,
        pending_bbq_reservations=1,
        pending_hall_reservations=2,
        published_news=11,
    )
    # Repos report different numbers; if the service hits them we'd see those.
    svc = _service(active=0, news=0, cache=cache)
    result = svc.overview(_admin())
    assert result.active_residents == 42
    assert result.total_reservations == 7
    assert result.pending_reservations == 3
    assert result.pending_bbq_reservations == 1
    assert result.pending_hall_reservations == 2
    assert result.published_news == 11
    # No new write happened, the cached value was simply returned.
    assert cache.set_calls == []


def test_permission_check_runs_before_cache_lookup():
    cache = FakeCache()
    cache.store[f"{AdminDashboardService.CACHE_KEY_PREFIX}:1"] = AdminDashboardOverview(
        active_residents=1,
        total_reservations=1,
        pending_reservations=1,
        pending_bbq_reservations=1,
        pending_hall_reservations=0,
        published_news=1,
    )
    svc = _service(cache=cache)
    with pytest.raises(PermissionDeniedError):
        svc.overview(_resident())
