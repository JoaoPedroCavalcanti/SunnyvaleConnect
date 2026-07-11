"""Smoke tests for the BBQ reservations API."""

from datetime import date, timedelta

import pytest
from django.core import mail
from django.urls import reverse

from units.models import Unit, UnitMembership
from tests_base.base_tests_user import BaseTestsUsers


pytestmark = pytest.mark.api


LIST_URL = reverse("bbq_reservations:list-create")


class BBQAPISmoke(BaseTestsUsers):
    def _future(self, days=10):
        return (date.today() + timedelta(days=days)).isoformat()

    def _seed_unit_with(self, user, apartment="1101", block="A"):
        kind = Unit.Kind.APARTMENT_BLOCK if block else Unit.Kind.APARTMENT
        unit = Unit.objects.create(
            kind=kind,
            apartment=apartment,
            block=block or "",
            status=Unit.Status.ACTIVE,
            condominium=self.condominium,
        )
        UnitMembership.objects.create(
            unit=unit,
            user=user,
            role=UnitMembership.Role.OWNER,
            status=UnitMembership.Status.ACTIVE,
        )
        return unit

    def test_anonymous_blocked(self):
        self.assertEqual(self.client.get(LIST_URL).status_code, 401)

    def test_regular_user_creates_for_self(self):
        house = self._seed_unit_with(self.user_a)
        self.authenticate(self.user_a)
        response = self.client.post(
            LIST_URL, data={"reservation_date": self._future()}
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(
            response.data["reservation_user"]["id"], self.user_a.id
        )
        self.assertEqual(response.data["unit"]["id"], house.id)
        self.assertEqual(response.data["unit"]["display_name"], "Apt 1101 / Block A")
        self.assertEqual(response.data["status"], "PENDING")

    def test_admin_creation_is_auto_approved(self):
        self._seed_unit_with(self.user_a)
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
        """Regression: front sending ``reservation_user`` with the
        logged-in user's id used to crash with 'You can not pass a
        reservation_user'."""
        self._seed_unit_with(self.user_a)
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
        self._seed_unit_with(self.user_a, "1101", "A")
        self._seed_unit_with(self.user_b, "1102", "A")
        self.authenticate(self.user_a)
        response = self.client.post(
            LIST_URL,
            data={
                "reservation_date": self._future(),
                "reservation_user": self.user_b.id,
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_user_without_unit_rejected(self):
        self.authenticate(self.user_a)
        response = self.client.post(
            LIST_URL, data={"reservation_date": self._future()}
        )
        self.assertEqual(response.status_code, 400)

    def test_30_day_window_is_per_apartment(self):
        """Roommate of the same apartment can't bypass the cool-down.
        Only APPROVED bookings count, so we seed an admin-created one."""
        house = self._seed_unit_with(self.user_a, "1101", "A")
        UnitMembership.objects.create(
            unit=house,
            user=self.user_b,
            role=UnitMembership.Role.RESIDENT,
            status=UnitMembership.Status.ACTIVE,
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

    def test_past_date_rejected(self):
        self._seed_unit_with(self.user_a)
        self.authenticate(self.user_a)
        past = (date.today() - timedelta(days=1)).isoformat()
        response = self.client.post(LIST_URL, data={"reservation_date": past})
        self.assertEqual(response.status_code, 400)

    def test_two_non_overlapping_slots_same_day(self):
        """Two apartments can share the same day if slots don't overlap.
        Booked by admin so both are APPROVED (PENDING don't occupy slot)."""
        self._seed_unit_with(self.user_a, "1101", "A")
        self._seed_unit_with(self.user_b, "1102", "A")
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
        self.assertEqual(r1.data["start_time"], "12:00:00")
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
        self._seed_unit_with(self.user_a)
        self.authenticate(self.user_a)
        r = self.client.post(
            LIST_URL, data={"reservation_date": self._future()}
        )
        self.assertEqual(r.status_code, 201, r.data)
        pk = r.data["id"]
        self.assertEqual(r.data["status"], "PENDING")

        self.authenticate(self.admin)
        approve_url = reverse(
            "bbq_reservations:approve", kwargs={"pk": pk}
        )
        approved = self.client.post(approve_url)
        self.assertEqual(approved.status_code, 200, approved.data)
        self.assertEqual(approved.data["status"], "APPROVED")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user_a.email])
        self.assertIn("barbecue area", mail.outbox[0].subject)

    def test_admin_rejects_pending_booking(self):
        self._seed_unit_with(self.user_a)
        self.authenticate(self.user_a)
        r = self.client.post(
            LIST_URL, data={"reservation_date": self._future()}
        )
        pk = r.data["id"]

        self.authenticate(self.admin)
        reject_url = reverse("bbq_reservations:reject", kwargs={"pk": pk})
        rejected = self.client.post(
            reject_url, data={"reason": "slot unavailable"}, format="json"
        )
        self.assertEqual(rejected.status_code, 200, rejected.data)
        self.assertEqual(rejected.data["status"], "REJECTED")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user_a.email])
        self.assertIn("barbecue area", mail.outbox[0].subject)
        self.assertIn("slot unavailable", mail.outbox[0].body)

    def test_admin_reject_without_reason_returns_400(self):
        self._seed_unit_with(self.user_a)
        self.authenticate(self.user_a)
        r = self.client.post(
            LIST_URL, data={"reservation_date": self._future()}
        )
        pk = r.data["id"]

        self.authenticate(self.admin)
        reject_url = reverse("bbq_reservations:reject", kwargs={"pk": pk})
        self.assertEqual(self.client.post(reject_url).status_code, 400)
        self.assertEqual(
            self.client.post(reject_url, data={"reason": ""}, format="json").status_code,
            400,
        )
        self.assertEqual(
            self.client.post(reject_url, data={"reason": "   "}, format="json").status_code,
            400,
        )

    def test_regular_user_cannot_approve(self):
        self._seed_unit_with(self.user_a)
        self.authenticate(self.user_a)
        r = self.client.post(
            LIST_URL, data={"reservation_date": self._future()}
        )
        pk = r.data["id"]
        approve_url = reverse(
            "bbq_reservations:approve", kwargs={"pk": pk}
        )
        self.assertEqual(self.client.post(approve_url).status_code, 403)

    def test_list_filtered_by_status(self):
        """Admin can query ?status=PENDING for the approval queue."""
        self._seed_unit_with(self.user_a, "1101", "A")
        self._seed_unit_with(self.user_b, "1102", "A")
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
