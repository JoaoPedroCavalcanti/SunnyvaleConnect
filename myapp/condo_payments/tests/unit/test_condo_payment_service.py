"""Unit tests for CondoPaymentService."""

from types import SimpleNamespace

import pytest

from condo_payments.repositories.condo_payment_repository import (
    ICondoPaymentRepository,
)
from condo_payments.services.condo_payment_service import CondoPaymentService
from shared.exceptions import BusinessRuleError, NotFoundError, PermissionDeniedError


pytestmark = pytest.mark.unit

TEST_CONDOMINIUM_ID = 1


class FakeCondoPaymentRepository(ICondoPaymentRepository):
    def __init__(self):
        self._items: dict[int, SimpleNamespace] = {}
        self._next_id = 1

    def list_all(self, *, condominium_id):
        return sorted(self._items.values(), key=lambda i: -i.id)

    def list_for_user(self, user_id, *, condominium_id):
        return [i for i in self._items.values() if i.payer_user_id == user_id]

    def get_by_id(self, pk):
        return self._items.get(int(pk))

    def list_by_ids(self, ids):
        return [self._items[i] for i in ids if i in self._items]

    def create(self, data):
        payer_user = data.get("payer_user")
        payer_user_id = getattr(payer_user, "id", None) or data.get("payer_user_id")
        if payer_user is None and payer_user_id is not None:
            payer_user = SimpleNamespace(
                id=payer_user_id,
                condominium_id=TEST_CONDOMINIUM_ID,
            )
        cleaned = {
            k: v
            for k, v in data.items()
            if k not in ("payer_user", "payer_user_id", "status")
        }
        item = SimpleNamespace(
            id=self._next_id,
            payer_user=payer_user,
            payer_user_id=payer_user_id,
            status=data.get("status", "pending"),
            **cleaned,
        )
        self._items[self._next_id] = item
        self._next_id += 1
        return item

    def update(self, instance, data):
        for k, v in data.items():
            setattr(instance, k, v)
        return instance

    def delete(self, instance):
        self._items.pop(instance.id, None)

    def bulk_set_status(self, instances, new_status):
        for inst in instances:
            inst.status = new_status


@pytest.fixture
def service():
    return CondoPaymentService(repository=FakeCondoPaymentRepository())


def _user(pk=1, is_staff=False):
    return SimpleNamespace(id=pk, is_staff=is_staff, condominium_id=TEST_CONDOMINIUM_ID)


def _admin():
    return _user(99, is_staff=True)


class TestListing:
    def test_admin_sees_all(self, service):
        service.create(_admin(), {"payer_user_id": 1, "status": "pending"})
        service.create(_admin(), {"payer_user_id": 2, "status": "pending"})
        assert len(service.list_for(_user(is_staff=True))) == 2

    def test_user_sees_only_own(self, service):
        service.create(_admin(), {"payer_user_id": 1, "status": "pending"})
        service.create(_admin(), {"payer_user_id": 2, "status": "pending"})
        assert len(service.list_for(_user(1))) == 1


class TestPermissions:
    def test_non_admin_cannot_create(self, service):
        with pytest.raises(PermissionDeniedError):
            service.create(_user(1), {"payer_user_id": 1, "status": "pending"})

    def test_non_admin_cannot_mark_paid(self, service):
        with pytest.raises(PermissionDeniedError):
            service.mark_as_paid(_user(1), [1])


class TestGetFor:
    def test_404_if_not_owner(self, service):
        item = service.create(_admin(), {"payer_user_id": 1, "status": "pending"})
        with pytest.raises(NotFoundError):
            service.get_for(_user(99), item.id)

    def test_admin_can_get_anything(self, service):
        item = service.create(_admin(), {"payer_user_id": 1, "status": "pending"})
        assert service.get_for(_admin(), item.id) is item


class TestMarkAsPaid:
    def test_empty_list_rejected(self, service):
        with pytest.raises(BusinessRuleError):
            service.mark_as_paid(_admin(), [])

    def test_non_list_rejected(self, service):
        with pytest.raises(BusinessRuleError):
            service.mark_as_paid(_admin(), "123")

    def test_unknown_id_rejected(self, service):
        with pytest.raises(BusinessRuleError):
            service.mark_as_paid(_admin(), [9999])

    def test_already_paid_rejected(self, service):
        item = service.create(_admin(), {"payer_user_id": 1, "status": "paid"})
        with pytest.raises(BusinessRuleError):
            service.mark_as_paid(_admin(), [item.id])

    def test_marks_pending_as_paid(self, service):
        a = service.create(_admin(), {"payer_user_id": 1, "status": "pending"})
        b = service.create(_admin(), {"payer_user_id": 1, "status": "pending"})
        service.mark_as_paid(_admin(), [a.id, b.id])
        assert a.status == "paid" and b.status == "paid"
