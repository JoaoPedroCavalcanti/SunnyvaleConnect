"""Smoke tests for the Hall reservations API."""

from datetime import date, timedelta

import pytest
from django.core import mail
from django.urls import reverse

from units.models import Unit, UnitMembership
from tests_base.base_tests_user import BaseTestsUsers


pytestmark = pytest.mark.api


LIST_URL = reverse("hall_reservations:list-create")
AVAILABILITY_URL = reverse("hall_reservations:availability")


class HallAPISmoke(BaseTestsUsers):
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
        self.assertEqual(self.client.get(AVAILABILITY_URL).status_code, 401)

    def test_resident_cannot_list(self):
        self.authenticate(self.user_a)
        self.assertEqual(self.client.get(LIST_URL).status_code, 403)

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

    def test_user_without_unit_rejected(self):
        self.authenticate(self.user_a)
        response = self.client.post(
            LIST_URL, data={"reservation_date": self._future()}
        )
        self.assertEqual(response.status_code, 400)

    def test_same_unit_can_book_again_within_30_days(self):
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
        self.assertEqual(r2.status_code, 201, r2.data)

    def test_admin_can_book_for_self_without_unit(self):
        self.authenticate(self.admin)
        response = self.client.post(
            LIST_URL, data={"reservation_date": self._future()}
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["status"], "APPROVED")
        self.assertIsNone(response.data["unit"])
        self.assertEqual(
            response.data["reservation_user"]["id"], self.admin.id
        )

    def test_two_slots_same_day_require_30_min_gap(self):
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
        self.assertEqual(r1.data["end_time"], "18:00:00")
        self.assertEqual(r1.data["status"], "APPROVED")

        adjacent = self.client.post(
            LIST_URL,
            data={
                "reservation_date": self._future(),
                "start_time": "18:00",
                "end_time": "22:00",
                "reservation_user": self.user_b.id,
            },
        )
        self.assertEqual(adjacent.status_code, 400, adjacent.data)
        self.assertIn("30 minutes", str(adjacent.data))

        r2 = self.client.post(
            LIST_URL,
            data={
                "reservation_date": self._future(),
                "start_time": "18:30",
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
        pk = r.data["id"]
        self.assertEqual(r.data["status"], "PENDING")

        self.authenticate(self.admin)
        approve_url = reverse(
            "hall_reservations:approve", kwargs={"pk": pk}
        )
        approved = self.client.post(approve_url)
        self.assertEqual(approved.status_code, 200, approved.data)
        self.assertEqual(approved.data["status"], "APPROVED")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user_a.email])
        self.assertIn("party hall", mail.outbox[0].subject)

    def test_admin_rejects_pending_booking(self):
        self._seed_unit_with(self.user_a)
        self.authenticate(self.user_a)
        r = self.client.post(
            LIST_URL, data={"reservation_date": self._future()}
        )
        pk = r.data["id"]

        self.authenticate(self.admin)
        reject_url = reverse("hall_reservations:reject", kwargs={"pk": pk})
        rejected = self.client.post(
            reject_url, data={"reason": "private event"}, format="json"
        )
        self.assertEqual(rejected.status_code, 200, rejected.data)
        self.assertEqual(rejected.data["status"], "REJECTED")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user_a.email])
        self.assertIn("party hall", mail.outbox[0].subject)
        self.assertIn("private event", mail.outbox[0].body)

    def test_admin_reject_without_reason_returns_400(self):
        self._seed_unit_with(self.user_a)
        self.authenticate(self.user_a)
        r = self.client.post(
            LIST_URL, data={"reservation_date": self._future()}
        )
        pk = r.data["id"]

        self.authenticate(self.admin)
        reject_url = reverse("hall_reservations:reject", kwargs={"pk": pk})
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
            "hall_reservations:approve", kwargs={"pk": pk}
        )
        self.assertEqual(self.client.post(approve_url).status_code, 403)

    def test_list_filtered_by_status(self):
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

    def test_availability_calendar_for_resident(self):
        self._seed_unit_with(self.user_a, "1101", "A")
        self._seed_unit_with(self.user_b, "1102", "A")
        day = self._future(10)

        self.authenticate(self.admin)
        approved = self.client.post(
            LIST_URL,
            data={
                "reservation_date": day,
                "start_time": "12:00",
                "end_time": "18:00",
                "reservation_user": self.user_a.id,
            },
        )
        self.assertEqual(approved.status_code, 201, approved.data)

        self.authenticate(self.user_b)
        response = self.client.get(
            AVAILABILITY_URL, {"from": day, "to": day}
        )
        self.assertEqual(response.status_code, 200, response.data)
        day_payload = response.data["days"][0]
        self.assertEqual(day_payload["status"], "partial")
        self.assertEqual(day_payload["free_slots"][0]["end_time"], "11:30:00")
        self.assertEqual(day_payload["free_slots"][1]["start_time"], "18:30:00")
