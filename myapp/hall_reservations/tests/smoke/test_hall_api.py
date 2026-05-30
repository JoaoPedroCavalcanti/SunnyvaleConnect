"""Smoke tests for the Hall reservations API."""

from datetime import date, timedelta

import pytest
from django.urls import reverse

from tests_base.base_tests_user import BaseTestsUsers


pytestmark = pytest.mark.api


LIST_URL = reverse("hall_reservations:list-create")


class HallAPISmoke(BaseTestsUsers):
    def _future(self, days=10):
        return (date.today() + timedelta(days=days)).isoformat()

    def test_anonymous_blocked(self):
        self.assertEqual(self.client.get(LIST_URL).status_code, 401)

    def test_regular_user_creates_for_self(self):
        self.authenticate(self.user_a)
        response = self.client.post(LIST_URL, data={"reservation_date": self._future()})
        self.assertEqual(response.status_code, 201, response.data)

    def test_admin_must_pass_reservation_user(self):
        self.authenticate(self.admin)
        response = self.client.post(LIST_URL, data={"reservation_date": self._future()})
        self.assertEqual(response.status_code, 400)
