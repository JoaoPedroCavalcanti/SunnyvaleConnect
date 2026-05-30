from unittest.mock import patch

from django.core import mail
from django.urls import reverse
from model_bakery import baker

from delivery_notification.models import DeliveryNotificationModel
from tests_base.base_tests_user import BaseTestsUsers


SEND_URL = reverse("delivery_notification:send_delivery_notification")
LIST_URL = reverse("delivery_notification:list_notifications")


def detail_url(pk: int) -> str:
    return reverse(
        "delivery_notification:detail_notification", kwargs={"pk": pk}
    )


class DeliveryNotificationPermissionTests(BaseTestsUsers):
    def test_non_admin_blocked_on_send(self):
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

    def test_non_admin_blocked_on_list(self):
        self.authenticate(self.user_a)
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 403)


class DeliveryNotificationCreateTests(BaseTestsUsers):
    def test_admin_send_notification(self):
        self.user_a.email = "user_a@example.com"
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
        self.assertIn("Delivery notification", mail.outbox[0].subject)
        self.assertIn("user_a@example.com", mail.outbox[0].to)

    def test_invalid_payload_returns_400(self):
        self.authenticate(self.admin)
        response = self.client.post(
            SEND_URL, data={"delivery_from": "iFood"}, format="json"
        )
        self.assertEqual(response.status_code, 400)


class DeliveryNotificationListDetailTests(BaseTestsUsers):
    def setUp(self):
        super().setUp()
        self.notif = baker.make(
            DeliveryNotificationModel, user_to_delivery=self.user_a
        )

    def test_admin_lists_all(self):
        self.authenticate(self.admin)
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data), 1)

    def test_admin_retrieves_detail(self):
        self.authenticate(self.admin)
        response = self.client.get(detail_url(self.notif.id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.notif.id)

    def test_detail_not_found(self):
        self.authenticate(self.admin)
        response = self.client.get(detail_url(999999))
        self.assertEqual(response.status_code, 404)
