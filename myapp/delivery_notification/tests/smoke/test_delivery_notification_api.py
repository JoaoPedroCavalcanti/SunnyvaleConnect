"""Smoke tests for the delivery notifications API."""

import pytest
from django.core import mail
from django.urls import reverse

from delivery_notification.models import DeliveryNotificationModel
from units.models import Unit, UnitMembership
from tests_base.base_tests_user import BaseTestsUsers


pytestmark = pytest.mark.api


SEND_URL = reverse("delivery_notification:send_delivery_notification")
LIST_URL = reverse("delivery_notification:list_notifications")
APARTMENTS_URL = reverse("delivery_notification:list_apartments")


def detail_url(pk):
    return reverse("delivery_notification:detail_notification", kwargs={"pk": pk})


def _create_active_unit_with_owner(user):
    unit = Unit.objects.create(
        kind=Unit.Kind.APARTMENT_BLOCK,
        apartment=user.apartment,
        block=user.block,
        status=Unit.Status.ACTIVE,
        condominium=user.condominium,
    )
    UnitMembership.objects.create(
        unit=unit,
        user=user,
        role=UnitMembership.Role.OWNER,
        status=UnitMembership.Status.ACTIVE,
    )
    return unit


class DeliveryNotificationAPISmoke(BaseTestsUsers):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.unit_a = _create_active_unit_with_owner(cls.user_a)

    def test_non_admin_blocked_send(self):
        self.authenticate(self.user_a)
        response = self.client.post(
            SEND_URL,
            data={
                "unit_id": self.unit_a.id,
                "title": "Package",
                "delivery_from": "iFood",
                "delivery_platform": "ifood",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_send(self):
        self.authenticate(self.admin)
        response = self.client.post(
            SEND_URL,
            data={
                "unit_id": self.unit_a.id,
                "title": "Package",
                "delivery_from": "iFood",
                "delivery_platform": "ifood",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(DeliveryNotificationModel.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user_a.email])
        self.assertEqual(response.data["notified_to"]["email"], self.user_a.email)
        self.assertEqual(response.data["notified_to"]["name"], self.user_a.full_name)
        self.assertEqual(
            response.data["display_name"],
            self.unit_a.display_name(),
        )

    def test_admin_list_apartments(self):
        self.authenticate(self.admin)
        response = self.client.get(APARTMENTS_URL)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["display_name"],
            self.unit_a.display_name(),
        )
        self.assertEqual(response.data[0]["holder_name"], self.user_a.full_name)
        self.assertEqual(response.data[0]["status"], Unit.Status.ACTIVE)

    def test_invalid_payload_400(self):
        self.authenticate(self.admin)
        response = self.client.post(
            SEND_URL, data={"delivery_from": "iFood"}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_detail_not_found(self):
        self.authenticate(self.admin)
        self.assertEqual(self.client.get(detail_url(99999)).status_code, 404)
