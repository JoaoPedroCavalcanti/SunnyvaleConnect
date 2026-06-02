"""Smoke tests for the BBQ reservations API."""

from datetime import date, timedelta

import pytest
from django.urls import reverse

from households.models import Household, HouseholdMembership
from tests_base.base_tests_user import BaseTestsUsers


pytestmark = pytest.mark.api


LIST_URL = reverse("bbq_reservations:list-create")


class BBQAPISmoke(BaseTestsUsers):
    def _future(self, days=10):
        return (date.today() + timedelta(days=days)).isoformat()

    def _seed_household_with(self, user, apartment="1101", block="A"):
        household = Household.objects.create(
            apartment=apartment, block=block, status=Household.Status.ACTIVE
        )
        HouseholdMembership.objects.create(
            household=household,
            user=user,
            role=HouseholdMembership.Role.HOLDER,
            status=HouseholdMembership.Status.ACTIVE,
        )
        return household

    def test_anonymous_blocked(self):
        self.assertEqual(self.client.get(LIST_URL).status_code, 401)

    def test_regular_user_creates_for_self(self):
        house = self._seed_household_with(self.user_a)
        self.authenticate(self.user_a)
        response = self.client.post(
            LIST_URL, data={"reservation_date": self._future()}
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(
            response.data["reservation_user"]["id"], self.user_a.id
        )
        self.assertEqual(response.data["household"]["id"], house.id)
        self.assertEqual(response.data["household"]["apartment"], "1101")

    def test_tolerates_passing_own_id(self):
        """Regression: front sending ``reservation_user`` with the
        logged-in user's id used to crash with 'You can not pass a
        reservation_user'."""
        self._seed_household_with(self.user_a)
        self.authenticate(self.user_a)
        response = self.client.post(
            LIST_URL,
            data={
                "reservation_date": self._future(),
                "reservation_user": self.user_a.id,
            },
        )
        self.assertEqual(response.status_code, 201, response.data)

    def test_regular_user_cannot_pass_other_user(self):
        self._seed_household_with(self.user_a, "1101", "A")
        self._seed_household_with(self.user_b, "1102", "A")
        self.authenticate(self.user_a)
        response = self.client.post(
            LIST_URL,
            data={
                "reservation_date": self._future(),
                "reservation_user": self.user_b.id,
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_user_without_household_rejected(self):
        self.authenticate(self.user_a)
        response = self.client.post(
            LIST_URL, data={"reservation_date": self._future()}
        )
        self.assertEqual(response.status_code, 400)

    def test_30_day_window_is_per_apartment(self):
        """Roommate of the same apartment can't bypass the cool-down."""
        house = self._seed_household_with(self.user_a, "1101", "A")
        HouseholdMembership.objects.create(
            household=house,
            user=self.user_b,
            role=HouseholdMembership.Role.RESIDENT,
            status=HouseholdMembership.Status.ACTIVE,
        )

        self.authenticate(self.user_a)
        r1 = self.client.post(
            LIST_URL, data={"reservation_date": self._future(5)}
        )
        self.assertEqual(r1.status_code, 201, r1.data)

        self.authenticate(self.user_b)
        r2 = self.client.post(
            LIST_URL, data={"reservation_date": self._future(15)}
        )
        self.assertEqual(r2.status_code, 400, r2.data)

    def test_admin_must_pass_reservation_user(self):
        self.authenticate(self.admin)
        response = self.client.post(
            LIST_URL, data={"reservation_date": self._future()}
        )
        self.assertEqual(response.status_code, 400)

    def test_past_date_rejected(self):
        self._seed_household_with(self.user_a)
        self.authenticate(self.user_a)
        past = (date.today() - timedelta(days=1)).isoformat()
        response = self.client.post(LIST_URL, data={"reservation_date": past})
        self.assertEqual(response.status_code, 400)

    def test_two_non_overlapping_slots_same_day(self):
        """Two apartments can share the same day if slots don't overlap."""
        self._seed_household_with(self.user_a, "1101", "A")
        self._seed_household_with(self.user_b, "1102", "A")

        self.authenticate(self.user_a)
        r1 = self.client.post(
            LIST_URL,
            data={
                "reservation_date": self._future(),
                "start_time": "12:00",
                "end_time": "18:00",
            },
        )
        self.assertEqual(r1.status_code, 201, r1.data)
        self.assertEqual(r1.data["start_time"], "12:00:00")

        self.authenticate(self.user_b)
        r2 = self.client.post(
            LIST_URL,
            data={
                "reservation_date": self._future(),
                "start_time": "18:00",
                "end_time": "22:00",
            },
        )
        self.assertEqual(r2.status_code, 201, r2.data)
