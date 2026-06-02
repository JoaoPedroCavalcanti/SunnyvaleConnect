"""Smoke tests for the Hall reservations API."""

from datetime import date, timedelta

import pytest
from django.urls import reverse

from households.models import Household, HouseholdMembership
from tests_base.base_tests_user import BaseTestsUsers


pytestmark = pytest.mark.api


LIST_URL = reverse("hall_reservations:list-create")


class HallAPISmoke(BaseTestsUsers):
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
        self.assertEqual(response.data["status"], "PENDING")

    def test_admin_creation_is_auto_approved(self):
        self._seed_household_with(self.user_a)
        self.authenticate(self.admin)
        response = self.client.post(
            LIST_URL,
            data={
                "reservation_date": self._future(),
                "reservation_user": self.user_a.id,
            },
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["status"], "APPROVED")

    def test_tolerates_passing_own_id(self):
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

    def test_user_without_household_rejected(self):
        self.authenticate(self.user_a)
        response = self.client.post(
            LIST_URL, data={"reservation_date": self._future()}
        )
        self.assertEqual(response.status_code, 400)

    def test_30_day_window_is_per_apartment(self):
        house = self._seed_household_with(self.user_a, "1101", "A")
        HouseholdMembership.objects.create(
            household=house,
            user=self.user_b,
            role=HouseholdMembership.Role.RESIDENT,
            status=HouseholdMembership.Status.ACTIVE,
        )
        self.authenticate(self.admin)
        r1 = self.client.post(
            LIST_URL,
            data={
                "reservation_date": self._future(5),
                "reservation_user": self.user_a.id,
            },
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

    def test_two_non_overlapping_slots_same_day(self):
        self._seed_household_with(self.user_a, "1101", "A")
        self._seed_household_with(self.user_b, "1102", "A")
        self.authenticate(self.admin)

        r1 = self.client.post(
            LIST_URL,
            data={
                "reservation_date": self._future(),
                "start_time": "12:00",
                "end_time": "18:00",
                "reservation_user": self.user_a.id,
            },
        )
        self.assertEqual(r1.status_code, 201, r1.data)
        self.assertEqual(r1.data["end_time"], "18:00:00")
        self.assertEqual(r1.data["status"], "APPROVED")

        r2 = self.client.post(
            LIST_URL,
            data={
                "reservation_date": self._future(),
                "start_time": "18:00",
                "end_time": "22:00",
                "reservation_user": self.user_b.id,
            },
        )
        self.assertEqual(r2.status_code, 201, r2.data)

    def test_admin_approves_pending_booking(self):
        self._seed_household_with(self.user_a)
        self.authenticate(self.user_a)
        r = self.client.post(
            LIST_URL, data={"reservation_date": self._future()}
        )
        pk = r.data["id"]
        self.assertEqual(r.data["status"], "PENDING")

        self.authenticate(self.admin)
        approve_url = reverse(
            "hall_reservations:approve", kwargs={"pk": pk}
        )
        approved = self.client.post(approve_url)
        self.assertEqual(approved.status_code, 200, approved.data)
        self.assertEqual(approved.data["status"], "APPROVED")

    def test_admin_rejects_pending_booking(self):
        self._seed_household_with(self.user_a)
        self.authenticate(self.user_a)
        r = self.client.post(
            LIST_URL, data={"reservation_date": self._future()}
        )
        pk = r.data["id"]

        self.authenticate(self.admin)
        reject_url = reverse("hall_reservations:reject", kwargs={"pk": pk})
        rejected = self.client.post(reject_url)
        self.assertEqual(rejected.status_code, 200, rejected.data)
        self.assertEqual(rejected.data["status"], "REJECTED")

    def test_regular_user_cannot_approve(self):
        self._seed_household_with(self.user_a)
        self.authenticate(self.user_a)
        r = self.client.post(
            LIST_URL, data={"reservation_date": self._future()}
        )
        pk = r.data["id"]
        approve_url = reverse(
            "hall_reservations:approve", kwargs={"pk": pk}
        )
        self.assertEqual(self.client.post(approve_url).status_code, 403)

    def test_list_filtered_by_status(self):
        self._seed_household_with(self.user_a, "1101", "A")
        self._seed_household_with(self.user_b, "1102", "A")
        self.authenticate(self.user_a)
        self.client.post(
            LIST_URL, data={"reservation_date": self._future(5)}
        )
        self.authenticate(self.user_b)
        self.client.post(
            LIST_URL, data={"reservation_date": self._future(10)}
        )
        self.authenticate(self.admin)
        self.client.post(
            LIST_URL,
            data={
                "reservation_date": self._future(20),
                "reservation_user": self.user_a.id,
            },
        )

        response = self.client.get(LIST_URL + "?status=PENDING")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        for item in response.data["results"]:
            self.assertEqual(item["status"], "PENDING")

        response = self.client.get(LIST_URL + "?status=APPROVED")
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["status"], "APPROVED")

    def test_invalid_status_filter_returns_400(self):
        self.authenticate(self.admin)
        response = self.client.get(LIST_URL + "?status=NOPE")
        self.assertEqual(response.status_code, 400)
