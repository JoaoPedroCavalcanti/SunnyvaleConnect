"""Smoke tests for the delivery notifications API."""

import pytest
from django.core import mail
from django.urls import reverse

from delivery_notification.models import DeliveryNotificationModel
from households.models import Household, HouseholdMembership
from tests_base.base_tests_user import BaseTestsUsers


pytestmark = pytest.mark.api


SEND_URL = reverse("delivery_notification:send_delivery_notification")
LIST_URL = reverse("delivery_notification:list_notifications")
APARTMENTS_URL = reverse("delivery_notification:list_apartments")


def detail_url(pk):
    return reverse("delivery_notification:detail_notification", kwargs={"pk": pk})


def _create_active_household_with_holder(user):
    household = Household.objects.create(
        apartment=user.apartment,
        block=user.block,
        status=Household.Status.ACTIVE,
    )
    HouseholdMembership.objects.create(
        household=household,
        user=user,
        role=HouseholdMembership.Role.HOLDER,
        status=HouseholdMembership.Status.ACTIVE,
    )
    return household


class DeliveryNotificationAPISmoke(BaseTestsUsers):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.household_a = _create_active_household_with_holder(cls.user_a)

    def test_non_admin_blocked_send(self):
        self.authenticate(self.user_a)
        response = self.client.post(
            SEND_URL,
            data={
                "apartment": self.user_a.apartment,
                "block": self.user_a.block,
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
                "apartment": self.user_a.apartment,
                "block": self.user_a.block,
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

    def test_admin_list_apartments(self):
        self.authenticate(self.admin)
        response = self.client.get(APARTMENTS_URL)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["apartment"], self.user_a.apartment)
        self.assertEqual(response.data[0]["holder_name"], self.user_a.full_name)
        self.assertEqual(response.data[0]["status"], Household.Status.ACTIVE)

    def test_invalid_payload_400(self):
        self.authenticate(self.admin)
        response = self.client.post(
            SEND_URL, data={"delivery_from": "iFood"}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_detail_not_found(self):
        self.authenticate(self.admin)
        self.assertEqual(self.client.get(detail_url(99999)).status_code, 404)
