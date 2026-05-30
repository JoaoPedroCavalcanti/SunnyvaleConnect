"""Unit tests for ServiceRequestService."""

from types import SimpleNamespace

import pytest

from service_requests.repositories.service_request_repository import (
    IServiceRequestRepository,
)
from service_requests.services.service_request_service import ServiceRequestService
from shared.exceptions import BusinessRuleError, NotFoundError


pytestmark = pytest.mark.unit


class FakeRepo(IServiceRequestRepository):
    def __init__(self):
        self._items: dict[int, SimpleNamespace] = {}
        self._next_id = 1

    def list_all(self):
        return list(self._items.values())

    def list_for_user(self, user_id):
        return [i for i in self._items.values() if i.requester_user_id == user_id]

    def get_by_id(self, pk):
        return self._items.get(int(pk))

    def create(self, data):
        item = SimpleNamespace(
            id=self._next_id,
            requester_user_id=getattr(data.get("requester_user"), "id", None),
            status=data.get("status", "requested"),
            **{k: v for k, v in data.items() if k != "requester_user"},
        )
        item.requester_user = data.get("requester_user")
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
    return ServiceRequestService(repository=FakeRepo())


def _user(pk=1, is_staff=False):
    return SimpleNamespace(id=pk, is_staff=is_staff)


def test_user_only_sees_own(service):
    u1, u2 = _user(1), _user(2)
    service.create({"requester_user": u1, "title": "a"})
    service.create({"requester_user": u2, "title": "b"})
    assert len(list(service.list_for(u1))) == 1


def test_admin_sees_all(service):
    service.create({"requester_user": _user(1), "title": "a"})
    service.create({"requester_user": _user(2), "title": "b"})
    assert len(list(service.list_for(_user(is_staff=True)))) == 2


def test_get_for_404_if_not_owner(service):
    item = service.create({"requester_user": _user(1), "title": "a"})
    with pytest.raises(NotFoundError):
        service.get_for(_user(99), item.id)


def test_set_status_accept(service):
    item = service.create({"requester_user": _user(1), "title": "a"})
    updated = service.set_status(item.id, "accept", {})
    assert updated.status == "accepted"


def test_set_status_decline(service):
    item = service.create({"requester_user": _user(1), "title": "a"})
    updated = service.set_status(item.id, "decline", {})
    assert updated.status == "declined"


def test_set_status_invalid_action(service):
    item = service.create({"requester_user": _user(1), "title": "a"})
    with pytest.raises(BusinessRuleError):
        service.set_status(item.id, "wat", {})


def test_update_empty_payload_rejected(service):
    item = service.create({"requester_user": _user(1), "title": "a"})
    with pytest.raises(BusinessRuleError):
        service.update(_user(1), item.id, {})
