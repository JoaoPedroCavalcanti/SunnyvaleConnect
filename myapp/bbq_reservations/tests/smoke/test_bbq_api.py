"""Smoke tests for the BBQ reservations API."""

from datetime import date, timedelta

import pytest
from django.urls import reverse

from tests_base.base_tests_user import BaseTestsUsers


pytestmark = pytest.mark.api


LIST_URL = reverse("bbq_reservations:list-create")


class BBQAPISmoke(BaseTestsUsers):
    def _future(self, days=10):
        return (date.today() + timedelta(days=days)).isoformat()

    def test_anonymous_blocked(self):
        self.assertEqual(self.client.get(LIST_URL).status_code, 401)

    def test_regular_user_creates_for_self(self):
        self.authenticate(self.user_a)
        response = self.client.post(LIST_URL, data={"reservation_date": self._future()})
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["reservation_user"], self.user_a.id)

    def test_regular_user_cannot_pass_reservation_user(self):
        self.authenticate(self.user_a)
        response = self.client.post(
            LIST_URL,
            data={"reservation_date": self._future(), "reservation_user": self.user_b.id},
        )
        self.assertEqual(response.status_code, 400)

    def test_admin_must_pass_reservation_user(self):
        self.authenticate(self.admin)
        response = self.client.post(LIST_URL, data={"reservation_date": self._future()})
        self.assertEqual(response.status_code, 400)

    def test_past_date_rejected(self):
        self.authenticate(self.user_a)
        past = (date.today() - timedelta(days=1)).isoformat()
        response = self.client.post(LIST_URL, data={"reservation_date": past})
        self.assertEqual(response.status_code, 400)
