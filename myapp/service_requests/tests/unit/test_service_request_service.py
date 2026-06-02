"""Unit tests for ServiceRequestService.

Pure-Python tests — no DB, no HTTP. We swap the repository for an
in-memory fake and verify the business rules:

  * residents only see / fetch their own requests, admins see all
  * create always pins ``requester`` to the caller and starts PENDING
  * owners can only edit / delete while PENDING
  * residents cannot smuggle admin fields (``status`` etc.) via update
  * ``respond`` requires admin + valid action + non-empty message and
    blocks double-answering
  * ``complete`` only works on ACCEPTED requests
  * filter validation rejects garbage values
"""

from types import SimpleNamespace

import pytest

from service_requests.models import ServiceRequestModel
from service_requests.repositories.service_request_repository import (
    IServiceRequestRepository,
)
from service_requests.services.service_request_service import ServiceRequestService
from shared.exceptions import (
    BusinessRuleError,
    NotFoundError,
    PermissionDeniedError,
)


pytestmark = pytest.mark.unit


class FakeRepo(IServiceRequestRepository):
    def __init__(self):
        self._items: dict[int, SimpleNamespace] = {}
        self._next_id = 1

    # --- helpers ----------------------------------------------------- #
    @staticmethod
    def _matches(item, status, priority, service_type) -> bool:
        if status and item.status != status:
            return False
        if priority and item.priority != priority:
            return False
        if service_type and item.service_type != service_type:
            return False
        return True

    # --- interface --------------------------------------------------- #
    def list_all(self, status=None, priority=None, service_type=None):
        return [
            i
            for i in self._items.values()
            if self._matches(i, status, priority, service_type)
        ]

    def list_for_user(
        self, user_id, status=None, priority=None, service_type=None
    ):
        return [
            i
            for i in self._items.values()
            if i.requester_id == user_id
            and self._matches(i, status, priority, service_type)
        ]

    def get_by_id(self, pk):
        return self._items.get(int(pk))

    def create(self, data):
        requester = data.get("requester")
        item = SimpleNamespace(
            id=self._next_id,
            requester=requester,
            requester_id=getattr(requester, "id", None),
            title=data.get("title", ""),
            description=data.get("description", ""),
            service_type=data.get(
                "service_type", ServiceRequestModel.ServiceType.OTHER
            ),
            location=data.get("location", ""),
            priority=data.get("priority", ServiceRequestModel.Priority.LOW),
            request_scheduled_date=data.get("request_scheduled_date"),
            status=data.get("status", ServiceRequestModel.Status.PENDING),
            admin_response=data.get("admin_response", ""),
            responded_by=data.get("responded_by"),
            responded_by_id=getattr(data.get("responded_by"), "id", None),
            responded_at=data.get("responded_at"),
        )
        self._items[self._next_id] = item
        self._next_id += 1
        return item

    def update(self, instance, data):
        for k, v in data.items():
            setattr(instance, k, v)
            if k == "responded_by":
                instance.responded_by_id = getattr(v, "id", None)
        return instance

    def delete(self, instance):
        self._items.pop(instance.id, None)

    def count_by_status(self, status=None):
        if not status:
            return len(self._items)
        return sum(1 for i in self._items.values() if i.status == status)


@pytest.fixture
def service():
    return ServiceRequestService(repository=FakeRepo())


def _user(pk=1, is_staff=False):
    return SimpleNamespace(id=pk, is_staff=is_staff)


# ---------------------------------------------------------------------- #
# create                                                                 #
# ---------------------------------------------------------------------- #
def test_create_pins_requester_to_caller(service):
    item = service.create(_user(7), {"title": "Leaking pipe"})
    assert item.requester_id == 7
    assert item.status == ServiceRequestModel.Status.PENDING


def test_create_ignores_admin_fields_in_payload(service):
    item = service.create(
        _user(7),
        {
            "title": "x",
            "status": "ACCEPTED",
            "admin_response": "boom",
            "responded_by": _user(99, is_staff=True),
        },
    )
    assert item.status == ServiceRequestModel.Status.PENDING
    assert item.admin_response == ""
    assert item.responded_by is None


# ---------------------------------------------------------------------- #
# list / get                                                             #
# ---------------------------------------------------------------------- #
def test_user_only_sees_own(service):
    service.create(_user(1), {"title": "a"})
    service.create(_user(2), {"title": "b"})
    assert len(list(service.list(_user(1)))) == 1


def test_admin_sees_all(service):
    service.create(_user(1), {"title": "a"})
    service.create(_user(2), {"title": "b"})
    assert len(list(service.list(_user(99, is_staff=True)))) == 2


def test_list_filters_validated(service):
    with pytest.raises(BusinessRuleError):
        service.list(_user(1, is_staff=True), status="WAT")


def test_list_filters_by_priority_case_insensitive(service):
    service.create(_user(1), {"title": "a", "priority": "HIGH"})
    service.create(_user(1), {"title": "b", "priority": "LOW"})
    assert (
        len(list(service.list(_user(1), priority="high"))) == 1
    )


def test_get_returns_for_owner(service):
    item = service.create(_user(1), {"title": "a"})
    assert service.get(_user(1), item.id).id == item.id


def test_get_404_for_non_owner(service):
    item = service.create(_user(1), {"title": "a"})
    with pytest.raises(NotFoundError):
        service.get(_user(99), item.id)


def test_get_works_for_admin(service):
    item = service.create(_user(1), {"title": "a"})
    assert service.get(_user(2, is_staff=True), item.id).id == item.id


# ---------------------------------------------------------------------- #
# update / delete                                                        #
# ---------------------------------------------------------------------- #
def test_owner_can_update_while_pending(service):
    item = service.create(_user(1), {"title": "a"})
    updated = service.update(_user(1), item.id, {"title": "b"})
    assert updated.title == "b"


def test_owner_cannot_update_after_admin_response(service):
    item = service.create(_user(1), {"title": "a"})
    service.respond(_user(99, is_staff=True), item.id, "accept", "ok")
    with pytest.raises(BusinessRuleError):
        service.update(_user(1), item.id, {"title": "b"})


def test_owner_cannot_set_status_via_update(service):
    item = service.create(_user(1), {"title": "a"})
    service.update(_user(1), item.id, {"status": "ACCEPTED", "title": "b"})
    fresh = service.get(_user(1), item.id)
    assert fresh.status == ServiceRequestModel.Status.PENDING
    assert fresh.title == "b"


def test_admin_can_update_anytime(service):
    item = service.create(_user(1), {"title": "a"})
    service.respond(_user(99, is_staff=True), item.id, "accept", "ok")
    service.update(
        _user(99, is_staff=True), item.id, {"title": "edited by admin"}
    )
    assert service.get(_user(99, is_staff=True), item.id).title == "edited by admin"


def test_owner_can_delete_while_pending(service):
    item = service.create(_user(1), {"title": "a"})
    service.delete(_user(1), item.id)
    with pytest.raises(NotFoundError):
        service.get(_user(1, is_staff=True), item.id)


def test_owner_cannot_delete_after_admin_response(service):
    item = service.create(_user(1), {"title": "a"})
    service.respond(_user(99, is_staff=True), item.id, "decline", "no thanks")
    with pytest.raises(BusinessRuleError):
        service.delete(_user(1), item.id)


def test_update_empty_payload_rejected(service):
    item = service.create(_user(1), {"title": "a"})
    with pytest.raises(BusinessRuleError):
        service.update(_user(1), item.id, {})


# ---------------------------------------------------------------------- #
# respond                                                                #
# ---------------------------------------------------------------------- #
def test_respond_accept_writes_status_and_metadata(service):
    item = service.create(_user(1), {"title": "a"})
    admin = _user(99, is_staff=True)
    updated = service.respond(admin, item.id, "accept", "  we will fix it  ")
    assert updated.status == ServiceRequestModel.Status.ACCEPTED
    assert updated.admin_response == "we will fix it"
    assert updated.responded_by_id == 99
    assert updated.responded_at is not None


def test_respond_decline_writes_status(service):
    item = service.create(_user(1), {"title": "a"})
    updated = service.respond(
        _user(99, is_staff=True), item.id, "decline", "out of scope"
    )
    assert updated.status == ServiceRequestModel.Status.DECLINED


def test_respond_requires_admin(service):
    item = service.create(_user(1), {"title": "a"})
    with pytest.raises(PermissionDeniedError):
        service.respond(_user(1), item.id, "accept", "hi")


def test_respond_rejects_invalid_action(service):
    item = service.create(_user(1), {"title": "a"})
    with pytest.raises(BusinessRuleError):
        service.respond(_user(99, is_staff=True), item.id, "wat", "msg")


def test_respond_requires_non_empty_message(service):
    item = service.create(_user(1), {"title": "a"})
    with pytest.raises(BusinessRuleError):
        service.respond(_user(99, is_staff=True), item.id, "accept", "   ")


def test_respond_blocks_double_answer(service):
    item = service.create(_user(1), {"title": "a"})
    admin = _user(99, is_staff=True)
    service.respond(admin, item.id, "accept", "ok")
    with pytest.raises(BusinessRuleError):
        service.respond(admin, item.id, "decline", "changed mind")


def test_respond_404_when_not_found(service):
    with pytest.raises(NotFoundError):
        service.respond(_user(99, is_staff=True), 12345, "accept", "ok")


# ---------------------------------------------------------------------- #
# complete                                                               #
# ---------------------------------------------------------------------- #
def test_complete_only_on_accepted(service):
    item = service.create(_user(1), {"title": "a"})
    admin = _user(99, is_staff=True)
    with pytest.raises(BusinessRuleError):
        service.complete(admin, item.id)  # still PENDING
    service.respond(admin, item.id, "accept", "ok")
    completed = service.complete(admin, item.id)
    assert completed.status == ServiceRequestModel.Status.COMPLETED


def test_complete_requires_admin(service):
    item = service.create(_user(1), {"title": "a"})
    service.respond(_user(99, is_staff=True), item.id, "accept", "ok")
    with pytest.raises(PermissionDeniedError):
        service.complete(_user(1), item.id)
