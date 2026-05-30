"""Unit tests for HallReservationService."""

from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from hall_reservations.repositories.hall_repository import IHallRepository
from hall_reservations.services.hall_service import HallReservationService
from shared.exceptions import BusinessRuleError, NotFoundError


pytestmark = pytest.mark.unit


class FakeHallRepository(IHallRepository):
    def __init__(self):
        self._items = []
        self._next_id = 1

    def list_all(self):
        return list(self._items)

    def get_by_id(self, pk):
        return next((i for i in self._items if i.id == pk), None)

    def exists_for_date(self, reservation_date):
        return any(i.reservation_date == reservation_date for i in self._items)

    def latest_date_for_user(self, user_id):
        dates = [i.reservation_date for i in self._items if i.reservation_user.id == user_id]
        return max(dates) if dates else None

    def create(self, data):
        item = SimpleNamespace(id=self._next_id, **data)
        self._next_id += 1
        self._items.append(item)
        return item

    def update(self, instance, data):
        for k, v in data.items():
            setattr(instance, k, v)
        return instance

    def delete(self, instance):
        self._items.remove(instance)


@pytest.fixture
def service():
    return HallReservationService(repository=FakeHallRepository())


def _user(pk=1, is_staff=False):
    return SimpleNamespace(id=pk, is_staff=is_staff)


def _future(days=10):
    return date.today() + timedelta(days=days)


def test_regular_user_creates_for_self(service):
    u = _user()
    item = service.create(u, {"reservation_date": _future()})
    assert item.reservation_user is u


def test_regular_user_cannot_pass_reservation_user(service):
    with pytest.raises(BusinessRuleError):
        service.create(_user(1), {"reservation_date": _future(), "reservation_user": _user(2)})


def test_admin_must_pass_reservation_user(service):
    with pytest.raises(BusinessRuleError):
        service.create(_user(is_staff=True), {"reservation_date": _future()})


def test_past_date_rejected(service):
    with pytest.raises(BusinessRuleError):
        service.create(_user(), {"reservation_date": date.today() - timedelta(days=1)})


def test_date_collision(service):
    d = _future()
    service.create(_user(1), {"reservation_date": d})
    with pytest.raises(BusinessRuleError):
        service.create(_user(2), {"reservation_date": d})


def test_30_day_window(service):
    service.create(_user(1), {"reservation_date": _future(5)})
    with pytest.raises(BusinessRuleError):
        service.create(_user(1), {"reservation_date": _future(15)})


def test_not_found_on_get(service):
    with pytest.raises(NotFoundError):
        service.get(999)
