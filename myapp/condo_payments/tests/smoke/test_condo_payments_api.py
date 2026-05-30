"""Smoke tests for the condo payments API."""

import pytest
from django.urls import reverse
from model_bakery import baker

from condo_payments.models import CondoPaymentModel
from tests_base.base_tests_user import BaseTestsUsers


pytestmark = pytest.mark.api


LIST_URL = reverse("condo_payments:list-create")
SET_PAID_URL = reverse("condo_payments:set-paid-status")


class CondoPaymentsAPISmoke(BaseTestsUsers):
    def test_anonymous_blocked(self):
        self.assertEqual(self.client.get(LIST_URL).status_code, 401)

    def test_regular_user_cannot_create(self):
        self.authenticate(self.user_a)
        response = self.client.post(
            LIST_URL,
            data={
                "payer_user": self.user_a.id,
                "title": "Fee",
                "payment_link": "http://pay/1",
                "amount": "100.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_can_create(self):
        self.authenticate(self.admin)
        response = self.client.post(
            LIST_URL,
            data={
                "payer_user": self.user_a.id,
                "title": "Fee",
                "payment_link": "http://pay/1",
                "amount": "100.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)

    def test_user_sees_only_own(self):
        baker.make(CondoPaymentModel, payer_user=self.user_a, _quantity=2)
        baker.make(CondoPaymentModel, payer_user=self.user_b, _quantity=3)
        self.authenticate(self.user_a)
        self.assertEqual(self.client.get(LIST_URL).data["count"], 2)

    def test_admin_set_paid(self):
        p1 = baker.make(CondoPaymentModel, payer_user=self.user_a, status="pending")
        self.authenticate(self.admin)
        response = self.client.patch(
            SET_PAID_URL, data={"paid_payment_ids": [p1.id]}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        p1.refresh_from_db()
        self.assertEqual(p1.status, "paid")

    def test_set_paid_empty_list_400(self):
        self.authenticate(self.admin)
        response = self.client.patch(
            SET_PAID_URL, data={"paid_payment_ids": []}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_set_paid_non_admin_blocked(self):
        self.authenticate(self.user_a)
        response = self.client.patch(
            SET_PAID_URL, data={"paid_payment_ids": [1]}, format="json"
        )
        self.assertEqual(response.status_code, 403)
