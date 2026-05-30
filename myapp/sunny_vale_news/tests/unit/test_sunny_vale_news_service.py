"""Unit tests for SunnyValeNewsService."""

from types import SimpleNamespace

import pytest

from shared.exceptions import NotFoundError, PermissionDeniedError
from sunny_vale_news.repositories.sunny_vale_news_repository import (
    ISunnyValeNewsRepository,
)
from sunny_vale_news.services.sunny_vale_news_service import SunnyValeNewsService


pytestmark = pytest.mark.unit


class FakeSunnyValeNewsRepository(ISunnyValeNewsRepository):
    def __init__(self):
        self._items: dict[int, SimpleNamespace] = {}
        self._next_id = 1

    def list_all(self):
        return list(self._items.values())

    def get_by_id(self, news_id):
        return self._items.get(int(news_id))

    def create(self, data):
        item = SimpleNamespace(id=self._next_id, **data)
        self._items[self._next_id] = item
        self._next_id += 1
        return item

    def update(self, instance, data):
        for k, v in data.items():
            setattr(instance, k, v)
        return instance

    def delete(self, instance):
        self._items.pop(instance.id, None)


@pytest.fixture
def service():
    return SunnyValeNewsService(repository=FakeSunnyValeNewsRepository())


def _admin():
    return SimpleNamespace(id=1, is_staff=True)


def _user():
    return SimpleNamespace(id=2, is_staff=False)


def test_admin_creates(service):
    item = service.create(_admin(), {"title": "hi", "description": "x", "author": "me"})
    assert service.get(item.id) is item


def test_regular_user_cannot_create(service):
    with pytest.raises(PermissionDeniedError):
        service.create(_user(), {"title": "hi", "description": "x", "author": "me"})


def test_get_not_found(service):
    with pytest.raises(NotFoundError):
        service.get(999)


def test_list(service):
    service.create(_admin(), {"title": "a", "description": "", "author": "me"})
    service.create(_admin(), {"title": "b", "description": "", "author": "me"})
    assert len(service.list()) == 2


def test_update_persists(service):
    item = service.create(_admin(), {"title": "x", "description": "", "author": "me"})
    updated = service.update(_admin(), item.id, {"title": "new"})
    assert updated.title == "new"


def test_regular_user_cannot_update(service):
    item = service.create(_admin(), {"title": "x", "description": "", "author": "me"})
    with pytest.raises(PermissionDeniedError):
        service.update(_user(), item.id, {"title": "new"})


def test_delete(service):
    item = service.create(_admin(), {"title": "x", "description": "", "author": "me"})
    service.delete(_admin(), item.id)
    with pytest.raises(NotFoundError):
        service.get(item.id)
