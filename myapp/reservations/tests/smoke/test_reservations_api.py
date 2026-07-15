from datetime import date, timedelta

import pytest
from django.urls import reverse

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
