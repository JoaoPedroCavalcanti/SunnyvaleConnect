"""Unit tests for SunnyValeNewsService."""

from types import SimpleNamespace

import pytest

from shared.exceptions import (
    BusinessRuleError,
    NotFoundError,
    PermissionDeniedError,
)
from sunny_vale_news.models import SunnyValeNewsModel
from sunny_vale_news.repositories.sunny_vale_news_repository import (
    ISunnyValeNewsRepository,
)
from sunny_vale_news.services.sunny_vale_news_service import SunnyValeNewsService


pytestmark = pytest.mark.unit

TEST_CONDOMINIUM_ID = 1


class FakeSunnyValeNewsRepository(ISunnyValeNewsRepository):
    def __init__(self):
        self._items: dict[int, SimpleNamespace] = {}
        self._next_id = 1

    def list_all(self, *, condominium_id):
        return [
            i
            for i in self._items.values()
            if getattr(i, "condominium_id", None) == condominium_id
        ]

    def list_by_kind(self, kind, *, condominium_id):
        return [
            i
            for i in self._items.values()
            if getattr(i, "kind", None) == kind
            and getattr(i, "condominium_id", None) == condominium_id
        ]

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

    def count_all(self, *, condominium_id):
        return len(
            [
                i
                for i in self._items.values()
                if getattr(i, "condominium_id", None) == condominium_id
            ]
        )


@pytest.fixture
def service():
    return SunnyValeNewsService(repository=FakeSunnyValeNewsRepository())


def _admin(full_name="João Pedro", role="ADMIN"):
    return SimpleNamespace(
        id=1,
        username="joao",
        is_staff=True,
        full_name=full_name,
        role=role,
        condominium_id=TEST_CONDOMINIUM_ID,
    )


def _user():
    return SimpleNamespace(
        id=2,
        username="bob",
        is_staff=False,
        full_name="Bob",
        role="RESIDENT",
        condominium_id=TEST_CONDOMINIUM_ID,
    )


def _payload(**overrides):
    data = {"title": "hi", "description": "x"}
    data.update(overrides)
    return data


def test_admin_creates(service):
    admin = _admin()
    item = service.create(admin, _payload())
    assert service.get(admin, item.id) is item


def test_create_stamps_authorship_from_user(service):
    admin = _admin(full_name="Maria", role="ADMIN")
    item = service.create(admin, _payload())
    assert item.author == "Maria"
    assert item.author_role == "ADMIN"
    assert item.created_by.username == "joao"


def test_create_falls_back_to_username_when_full_name_blank(service):
    bare_admin = SimpleNamespace(
        id=1,
        username="joao",
        is_staff=True,
        full_name="",
        role="ADMIN",
        condominium_id=TEST_CONDOMINIUM_ID,
    )
    item = service.create(bare_admin, _payload())
    assert item.author == "joao"


def test_create_ignores_author_in_payload(service):
    item = service.create(
        _admin(full_name="Real Admin"),
        _payload(author="Evil Hacker", author_role="HACKER"),
    )
    assert item.author == "Real Admin"
    assert item.author_role == "ADMIN"


def test_create_accepts_explicit_kind(service):
    item = service.create(
        _admin(),
        _payload(kind=SunnyValeNewsModel.Kind.MAINTENANCE),
    )
    assert item.kind == SunnyValeNewsModel.Kind.MAINTENANCE


def test_regular_user_cannot_create(service):
    with pytest.raises(PermissionDeniedError):
        service.create(_user(), _payload())


def test_get_not_found(service):
    with pytest.raises(NotFoundError):
        service.get(_admin(), 999)


def test_list(service):
    admin = _admin()
    service.create(admin, _payload(title="a"))
    service.create(admin, _payload(title="b"))
    assert len(service.list(admin)) == 2


def test_list_filters_by_kind(service):
    admin = _admin()
    service.create(admin, _payload(kind=SunnyValeNewsModel.Kind.NOTICE))
    service.create(admin, _payload(kind=SunnyValeNewsModel.Kind.EVENT))
    notices = list(service.list(admin, kind=SunnyValeNewsModel.Kind.NOTICE))
    events = list(service.list(admin, kind=SunnyValeNewsModel.Kind.EVENT))
    assert len(notices) == 1
    assert len(events) == 1


def test_list_invalid_kind_filter_rejected(service):
    with pytest.raises(BusinessRuleError):
        list(service.list(_admin(), kind="GHOST"))


def test_update_persists(service):
    admin = _admin()
    item = service.create(admin, _payload())
    updated = service.update(admin, item.id, {"title": "new"})
    assert updated.title == "new"


def test_update_does_not_overwrite_authorship(service):
    admin = _admin(full_name="Original Admin")
    item = service.create(admin, _payload())
    service.update(
        _admin(full_name="Other Admin"),
        item.id,
        {"title": "edited", "author": "Hijacker", "author_role": "HACKER"},
    )
    assert item.author == "Original Admin"
    assert item.author_role == "ADMIN"


def test_regular_user_cannot_update(service):
    admin = _admin()
    item = service.create(admin, _payload())
    with pytest.raises(PermissionDeniedError):
        service.update(_user(), item.id, {"title": "new"})


def test_delete(service):
    admin = _admin()
    item = service.create(admin, _payload())
    service.delete(admin, item.id)
    with pytest.raises(NotFoundError):
        service.get(admin, item.id)
