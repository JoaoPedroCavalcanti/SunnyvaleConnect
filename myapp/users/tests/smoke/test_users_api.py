"""Smoke tests for the users API. One happy + one sad case per endpoint."""

import pytest
from django.urls import reverse

from tests_base.base_tests_user import BaseTestsUsers


pytestmark = pytest.mark.api


LIST_URL = reverse("users:users-api-list")
ME_URL = reverse("users:users-api-me")


def detail_url(pk: int) -> str:
    return reverse("users:users-api-detail", kwargs={"pk": pk})


class UsersAPISmoke(BaseTestsUsers):
    def test_anonymous_blocked(self):
        self.assertEqual(self.client.get(LIST_URL).status_code, 401)

    def test_anonymous_can_register(self):
        response = self.client.post(LIST_URL, data=self.create_random_user_from_faker())
        self.assertEqual(response.status_code, 201)

    def test_regular_user_lists_only_self(self):
        self.authenticate(self.user_a)
        results = self.client.get(LIST_URL).data["results"]
        self.assertEqual(len(results), 1)

    def test_admin_lists_all(self):
        self.authenticate(self.admin)
        self.assertGreaterEqual(self.client.get(LIST_URL).data["count"], 3)

    def test_me_returns_current_user(self):
        self.authenticate(self.user_a)
        response = self.client.get(ME_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.user_a.id)

    def test_user_detail_404_for_others(self):
        self.authenticate(self.user_a)
        self.assertEqual(self.client.get(detail_url(self.user_b.id)).status_code, 404)

    def test_weak_password_rejected(self):
        payload = self.create_random_user_from_faker()
        payload["password"] = "a"
        response = self.client.post(LIST_URL, data=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.data)

    def test_duplicate_email_rejected(self):
        payload = self.create_random_user_from_faker()
        payload["email"] = self.user_a.email
        response = self.client.post(LIST_URL, data=payload)
        self.assertEqual(response.status_code, 400)

    def test_duplicate_cpf_rejected(self):
        payload = self.create_random_user_from_faker()
        payload["cpf"] = self.user_a.cpf
        response = self.client.post(LIST_URL, data=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("cpf", response.data)

    def test_invalid_cpf_rejected(self):
        payload = self.create_random_user_from_faker()
        payload["cpf"] = "11111111111"
        response = self.client.post(LIST_URL, data=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("cpf", response.data)

    def test_admin_can_delete_user(self):
        self.authenticate(self.admin)
        self.assertEqual(
            self.client.delete(detail_url(self.user_a.id)).status_code, 204
        )


LOGIN_URL = "/api/token/"


class LoginAPISmoke(BaseTestsUsers):
    def test_active_user_gets_tokens(self):
        response = self.client.post(
            LOGIN_URL,
            data={"username": self.user_a.username, "password": "Abcd123!"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_invalid_credentials_returns_401(self):
        response = self.client.post(
            LOGIN_URL,
            data={"username": self.user_a.username, "password": "wrong"},
            format="json",
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["code"], "invalid_credentials")

    def test_pending_user_returns_403_with_household_info(self):
        from households.models import Household, HouseholdMembership

        self.user_a.is_active = False
        self.user_a.save()
        household = Household.objects.create(
            apartment="701",
            block="C",
            status=Household.Status.PENDING_ADMIN,
        )
        HouseholdMembership.objects.create(
            household=household,
            user=self.user_a,
            role=HouseholdMembership.Role.HOLDER,
            status=HouseholdMembership.Status.PENDING_ADMIN,
        )

        response = self.client.post(
            LOGIN_URL,
            data={"username": self.user_a.username, "password": "Abcd123!"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["code"], "pending_household_approval")
        self.assertEqual(response.data["household"]["apartment"], "701")
