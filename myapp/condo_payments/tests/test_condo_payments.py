from django.urls import reverse, NoReverseMatch
from model_bakery import baker

from condo_payments.models import CondoPaymentModel
from tests_base.base_tests_user import BaseTestsUsers


def _list_url() -> str:
    try:
        return reverse("condo_payments_router-list")
    except NoReverseMatch:
        return "/condo_payments/"


def _detail_url(pk: int) -> str:
    try:
        return reverse("condo_payments_router-detail", kwargs={"pk": pk})
    except NoReverseMatch:
        return f"/condo_payments/{pk}/"


def _set_paid_url() -> str:
    try:
        return reverse("condo_payments_router-set-paid-status")
    except NoReverseMatch:
        return "/condo_payments/set_paid_status/"


LIST_URL = _list_url()
SET_PAID_URL = _set_paid_url()


class CondoPaymentsPermissionTests(BaseTestsUsers):
    def test_anonymous_blocked(self):
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 401)

    def test_regular_user_can_only_read(self):
        self.authenticate(self.user_a)
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)

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


class CondoPaymentsAdminTests(BaseTestsUsers):
    def test_admin_can_create(self):
        self.authenticate(self.admin)
        response = self.client.post(
            LIST_URL,
            data={
                "payer_user": self.user_a.id,
                "title": "May fee",
                "payment_link": "http://pay/1",
                "amount": "100.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)


class CondoPaymentsQuerysetTests(BaseTestsUsers):
    def test_user_only_sees_own_payments(self):
        baker.make(CondoPaymentModel, payer_user=self.user_a, _quantity=2)
        baker.make(CondoPaymentModel, payer_user=self.user_b, _quantity=3)

        self.authenticate(self.user_a)
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)

    def test_admin_sees_all_payments(self):
        baker.make(CondoPaymentModel, payer_user=self.user_a, _quantity=2)
        baker.make(CondoPaymentModel, payer_user=self.user_b, _quantity=3)

        self.authenticate(self.admin)
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 5)


class CondoPaymentsSetPaidStatusTests(BaseTestsUsers):
    def setUp(self):
        super().setUp()
        self.p1 = baker.make(CondoPaymentModel, payer_user=self.user_a, status="pending")
        self.p2 = baker.make(CondoPaymentModel, payer_user=self.user_a, status="pending")
        self.already_paid = baker.make(
            CondoPaymentModel, payer_user=self.user_a, status="paid"
        )

    def test_non_admin_blocked(self):
        self.authenticate(self.user_a)
        response = self.client.patch(
            SET_PAID_URL,
            data={"paid_payment_ids": [self.p1.id]},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_can_mark_paid(self):
        self.authenticate(self.admin)
        response = self.client.patch(
            SET_PAID_URL,
            data={"paid_payment_ids": [self.p1.id, self.p2.id]},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.assertEqual(self.p1.status, "paid")
        self.assertEqual(self.p2.status, "paid")

    def test_empty_list_returns_400(self):
        self.authenticate(self.admin)
        response = self.client.patch(
            SET_PAID_URL, data={"paid_payment_ids": []}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_already_paid_or_unknown_ids_rejected(self):
        self.authenticate(self.admin)
        response = self.client.patch(
            SET_PAID_URL,
            data={"paid_payment_ids": [self.already_paid.id, 999_999]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
