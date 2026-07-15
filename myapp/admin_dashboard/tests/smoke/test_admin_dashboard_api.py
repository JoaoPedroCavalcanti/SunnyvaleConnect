from datetime import date, timedelta

import pytest
from django.core.cache import cache
from django.urls import reverse
from model_bakery import baker

from reservations.models import ReservableLocation, Reservation
from sunny_vale_news.models import SunnyValeNewsModel
from tests_base.base_tests_user import BaseTestsUsers


pytestmark = pytest.mark.api
URL = reverse("admin_dashboard:overview")


class AdminDashboardOverviewSmoke(BaseTestsUsers):
    def setUp(self):
        super().setUp()
        cache.clear()

    def tearDown(self):
        cache.clear()
        super().tearDown()

    def test_anonymous_blocked(self):
        self.assertEqual(self.client.get(URL).status_code, 401)

    def test_resident_forbidden(self):
        self.authenticate(self.user_a)
        self.assertEqual(self.client.get(URL).status_code, 403)

    def test_admin_gets_generic_reservation_counts(self):
        location = baker.make(
            ReservableLocation,
            condominium=self.condominium,
        )
        tomorrow = date.today() + timedelta(days=1)
        baker.make(
            Reservation,
            condominium=self.condominium,
            location=location,
            reservation_date=tomorrow,
            status=Reservation.Status.APPROVED,
            _quantity=2,
        )
        baker.make(
            Reservation,
            condominium=self.condominium,
            location=location,
            reservation_date=tomorrow,
            status=Reservation.Status.PENDING,
            _quantity=3,
        )
        baker.make(
            Reservation,
            condominium=self.condominium,
            location=location,
            reservation_date=tomorrow,
            status=Reservation.Status.REJECTED,
        )
        baker.make(
            SunnyValeNewsModel,
            condominium=self.condominium,
            _quantity=2,
        )

        self.authenticate(self.admin)
        response = self.client.get(URL)

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["active_residents"], 3)
        self.assertEqual(response.data["total_reservations"], 2)
        self.assertEqual(response.data["pending_reservations"], 3)
        self.assertEqual(response.data["published_news"], 2)
        self.assertNotIn("pending_bbq_reservations", response.data)
        self.assertNotIn("pending_hall_reservations", response.data)

    def test_overview_response_is_cached(self):
        self.authenticate(self.admin)
        first = self.client.get(URL)
        baker.make(
            SunnyValeNewsModel,
            condominium=self.condominium,
            _quantity=3,
        )
        second = self.client.get(URL)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.data["published_news"], 0)
