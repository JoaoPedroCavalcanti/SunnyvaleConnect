from datetime import date, datetime, time, timedelta
from unittest.mock import patch

import pytest
from django.urls import reverse

from reservations.models import ReservableLocation, Reservation
from tests_base.base_tests_user import BaseTestsUsers
from units.models import Unit, UnitMembership


pytestmark = pytest.mark.api


class ReservationsAPISmoke(BaseTestsUsers):
    def _create_location(self, name="Party Hall", icon="celebration"):
        self.authenticate(self.admin)
        response = self.client.post(
            reverse("reservations:location-list-create"),
            {
                "condominium_id": self.condominium.id,
                "name": name,
                "icon": icon,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def _seed_membership(self, user):
        unit = Unit.objects.create(
            condominium=self.condominium,
            kind=Unit.Kind.APARTMENT,
            apartment="101",
        )
        UnitMembership.objects.create(
            unit=unit,
            user=user,
            role=UnitMembership.Role.RESIDENT,
            status=UnitMembership.Status.ACTIVE,
        )
        return unit

    def test_location_catalog_is_tenant_visible_and_archived(self):
        location = self._create_location()
        self.authenticate(self.user_a)
        listing = self.client.get(
            reverse("reservations:location-list-create")
        )
        self.assertEqual(listing.status_code, 200, listing.data)
        self.assertEqual([item["id"] for item in listing.data], [location["id"]])
        self.assertEqual(listing.data[0]["icon"], "celebration")

        self.authenticate(self.admin)
        detail = reverse(
            "reservations:location-detail",
            kwargs={"pk": location["id"]},
        )
        self.assertEqual(self.client.delete(detail).status_code, 204)

    def test_resident_creates_pending_reservation(self):
        location = self._create_location()
        self._seed_membership(self.user_a)
        self.authenticate(self.user_a)
        response = self.client.post(
            reverse("reservations:reservation-list-create"),
            {
                "location_id": location["id"],
                "reservation_date": (
                    date.today() + timedelta(days=5)
                ).isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["status"], "PENDING")
        self.assertEqual(
            response.data["reservation_user"]["id"], self.user_a.id
        )

    def test_pending_resident_and_approved_admin_can_edit(self):
        location = self._create_location()
        self._seed_membership(self.user_a)
        self.authenticate(self.user_a)
        created = self.client.post(
            reverse("reservations:reservation-list-create"),
            {
                "location_id": location["id"],
                "reservation_date": (
                    date.today() + timedelta(days=5)
                ).isoformat(),
                "start_time": "10:00:00",
                "end_time": "12:00:00",
                "guest_count": 4,
            },
            format="json",
        )
        detail_url = reverse(
            "reservations:reservation-detail",
            kwargs={"pk": created.data["id"]},
        )

        resident_patch = self.client.patch(
            detail_url,
            {"guest_count": 6},
            format="json",
        )
        self.assertEqual(
            resident_patch.status_code, 200, resident_patch.data
        )

        self.authenticate(self.admin)
        approve_url = reverse(
            "reservations:reservation-approve",
            kwargs={"pk": created.data["id"]},
        )
        approved = self.client.post(approve_url, {}, format="json")
        self.assertEqual(approved.status_code, 200, approved.data)
        admin_patch = self.client.patch(
            detail_url,
            {
                "start_time": "13:00:00",
                "end_time": "15:00:00",
                "guest_count": 10,
            },
            format="json",
        )
        self.assertEqual(admin_patch.status_code, 200, admin_patch.data)
        self.assertEqual(admin_patch.data["start_time"], "13:00:00")
        self.assertEqual(admin_patch.data["guest_count"], 10)
        immutable_location = self.client.patch(
            detail_url,
            {"location_id": 999},
            format="json",
        )
        self.assertEqual(
            immutable_location.status_code,
            400,
            immutable_location.data,
        )
        self.assertIn("location_id", immutable_location.data)

        self.authenticate(self.user_a)
        forbidden = self.client.patch(
            detail_url,
            {"guest_count": 12},
            format="json",
        )
        self.assertEqual(forbidden.status_code, 403, forbidden.data)

    def test_reservation_today_cannot_start_in_the_past(self):
        location = self._create_location()
        self._seed_membership(self.user_a)
        self.authenticate(self.user_a)

        with (
            patch(
                "reservations.services.reservation_service.timezone.localdate",
                return_value=date(2026, 7, 15),
            ),
            patch(
                "reservations.services.reservation_service.timezone.localtime",
                return_value=datetime(2026, 7, 15, 15, 43),
            ),
        ):
            response = self.client.post(
                reverse("reservations:reservation-list-create"),
                {
                    "location_id": location["id"],
                    "reservation_date": "2026-07-15",
                    "start_time": "07:00:00",
                    "end_time": "08:00:00",
                },
                format="json",
            )

        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("start_time", response.data)

    def test_reservations_can_be_filtered_by_period(self):
        location_data = self._create_location()
        unit = self._seed_membership(self.user_a)
        location = ReservableLocation.objects.get(pk=location_data["id"])
        today = date(2026, 7, 15)
        past = Reservation.objects.create(
            condominium=self.condominium,
            location=location,
            unit=unit,
            reservation_user=self.user_a,
            reservation_date=today - timedelta(days=1),
        )
        future = Reservation.objects.create(
            condominium=self.condominium,
            location=location,
            unit=unit,
            reservation_user=self.user_a,
            reservation_date=today + timedelta(days=1),
        )
        expired_today = Reservation.objects.create(
            condominium=self.condominium,
            location=location,
            unit=unit,
            reservation_user=self.user_a,
            reservation_date=today,
            start_time=time(7),
            end_time=time(8),
        )
        ongoing = Reservation.objects.create(
            condominium=self.condominium,
            location=location,
            unit=unit,
            reservation_user=self.user_a,
            reservation_date=today,
            start_time=time(15),
            end_time=time(16),
        )
        self.authenticate(self.user_a)

        with (
            patch(
                "reservations.services.reservation_service.timezone.localdate",
                return_value=today,
            ),
            patch(
                "reservations.services.reservation_service.timezone.localtime",
                return_value=datetime(2026, 7, 15, 15, 43),
            ),
        ):
            future_response = self.client.get(
                reverse("reservations:reservation-list-create")
                + "?period=future"
            )
            past_response = self.client.get(
                reverse("reservations:reservation-list-create")
                + "?period=past"
            )

        self.assertEqual(
            future_response.status_code, 200, future_response.data
        )
        self.assertEqual(
            past_response.status_code, 200, past_response.data
        )
        future_ids = {
            item["id"] for item in future_response.data["results"]
        }
        past_ids = {
            item["id"] for item in past_response.data["results"]
        }
        self.assertEqual(future_ids, {future.id, ongoing.id})
        self.assertEqual(past_ids, {past.id, expired_today.id})
        self.assertTrue(future_ids.isdisjoint(past_ids))

    def test_delete_rejects_rejected_and_past_reservations(self):
        location_data = self._create_location()
        unit = self._seed_membership(self.user_a)
        location = ReservableLocation.objects.get(pk=location_data["id"])
        rejected = Reservation.objects.create(
            condominium=self.condominium,
            location=location,
            unit=unit,
            reservation_user=self.user_a,
            reservation_date=date.today() + timedelta(days=2),
            start_time=time(10),
            end_time=time(12),
            status=Reservation.Status.REJECTED,
        )
        past = Reservation.objects.create(
            condominium=self.condominium,
            location=location,
            unit=unit,
            reservation_user=self.user_a,
            reservation_date=date.today() - timedelta(days=1),
            start_time=time(10),
            end_time=time(12),
            status=Reservation.Status.PENDING,
        )
        self.authenticate(self.user_a)

        rejected_response = self.client.delete(
            reverse(
                "reservations:reservation-detail",
                kwargs={"pk": rejected.id},
            )
        )
        past_response = self.client.delete(
            reverse(
                "reservations:reservation-detail",
                kwargs={"pk": past.id},
            )
        )

        self.assertEqual(rejected_response.status_code, 400)
        self.assertIn("status", rejected_response.data)
        self.assertEqual(past_response.status_code, 400)
        self.assertIn("reservation_date", past_response.data)
        self.assertTrue(Reservation.objects.filter(pk=rejected.id).exists())
        self.assertTrue(Reservation.objects.filter(pk=past.id).exists())

    def test_resident_cannot_create_location(self):
        self.authenticate(self.user_a)
        response = self.client.post(
            reverse("reservations:location-list-create"),
            {
                "condominium_id": self.condominium.id,
                "name": "Pool",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_location_rejects_unknown_icon(self):
        self.authenticate(self.admin)
        response = self.client.post(
            reverse("reservations:location-list-create"),
            {
                "condominium_id": self.condominium.id,
                "name": "Pool",
                "icon": "pool",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("icon", response.data)

    def test_conflict_is_scoped_to_the_same_location(self):
        first_location = self._create_location("Barbecue A")
        second_location = self._create_location("Barbecue B")
        reservation_url = reverse(
            "reservations:reservation-list-create"
        )
        reservation_date = date.today() + timedelta(days=5)
        payload = {
            "location_id": first_location["id"],
            "reservation_date": reservation_date.isoformat(),
            "start_time": "18:00:00",
            "end_time": "20:00:00",
        }

        self.authenticate(self.admin)
        first = self.client.post(reservation_url, payload, format="json")
        conflict = self.client.post(
            reservation_url, payload, format="json"
        )
        other_location = self.client.post(
            reservation_url,
            {**payload, "location_id": second_location["id"]},
            format="json",
        )

        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(conflict.status_code, 400, conflict.data)
        self.assertEqual(
            other_location.status_code, 201, other_location.data
        )
