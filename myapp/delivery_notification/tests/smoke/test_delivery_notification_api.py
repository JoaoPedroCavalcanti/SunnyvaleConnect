"""Smoke tests for the delivery notifications API."""

import pytest
from django.core import mail
from django.urls import reverse

from delivery_notification.models import DeliveryNotificationModel
from tests_base.base_tests_user import BaseTestsUsers


pytestmark = pytest.mark.api


SEND_URL = reverse("delivery_notification:send_delivery_notification")
LIST_URL = reverse("delivery_notification:list_notifications")


def detail_url(pk):
    return reverse("delivery_notification:detail_notification", kwargs={"pk": pk})


class DeliveryNotificationAPISmoke(BaseTestsUsers):
    def test_non_admin_blocked_send(self):
        self.authenticate(self.user_a)
        response = self.client.post(
            SEND_URL,
            data={
                "user_to_delivery": self.user_a.id,
                "title": "Package",
                "delivery_from": "iFood",
                "delivery_platform": "ifood",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_send(self):
        self.user_a.email = "ua@example.com"
        self.user_a.save()
        self.authenticate(self.admin)
        response = self.client.post(
            SEND_URL,
            data={
                "user_to_delivery": self.user_a.id,
                "title": "Package",
                "delivery_from": "iFood",
                "delivery_platform": "ifood",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(DeliveryNotificationModel.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_invalid_payload_400(self):
        self.authenticate(self.admin)
        response = self.client.post(
            SEND_URL, data={"delivery_from": "iFood"}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_detail_not_found(self):
        self.authenticate(self.admin)
        self.assertEqual(self.client.get(detail_url(99999)).status_code, 404)
