"""Smoke tests for the admin dashboard overview endpoint."""

from datetime import date, time, timedelta

import pytest
from django.core.cache import cache
from django.urls import reverse
from model_bakery import baker

from bbq_reservations.models import BBQReservationModel
from hall_reservations.models import HallReservationModel
from sunny_vale_news.models import SunnyValeNewsModel
from tests_base.base_tests_user import BaseTestsUsers


pytestmark = pytest.mark.api


URL = reverse("admin_dashboard:overview")


class AdminDashboardOverviewSmoke(BaseTestsUsers):
    def setUp(self):
        super().setUp()
        # LocMemCache is process-wide; clear it so counts don't leak between tests.
        cache.clear()

    def tearDown(self):
        cache.clear()
        super().tearDown()

    def test_anonymous_blocked(self):
        self.assertEqual(self.client.get(URL).status_code, 401)

    def test_resident_forbidden(self):
        self.authenticate(self.user_a)
        self.assertEqual(self.client.get(URL).status_code, 403)

    def test_admin_gets_aggregated_counts(self):
        # 1 approved + 1 pending + 1 rejected BBQ
        tomorrow = date.today() + timedelta(days=1)
        baker.make(
            BBQReservationModel,
            reservation_date=tomorrow,
            start_time=time(10, 0),
            end_time=time(11, 0),
            status=BBQReservationModel.Status.APPROVED,
        )
        baker.make(
            BBQReservationModel,
            reservation_date=tomorrow,
            start_time=time(12, 0),
            end_time=time(13, 0),
            status=BBQReservationModel.Status.PENDING,
        )
        baker.make(
            BBQReservationModel,
            reservation_date=tomorrow,
            start_time=time(14, 0),
            end_time=time(15, 0),
            status=BBQReservationModel.Status.REJECTED,
        )
        # 1 approved Hall + 2 pending Hall
        baker.make(
            HallReservationModel,
            reservation_date=tomorrow,
            start_time=time(10, 0),
            end_time=time(11, 0),
            status=HallReservationModel.Status.APPROVED,
        )
        baker.make(
            HallReservationModel,
            reservation_date=tomorrow,
            start_time=time(12, 0),
            end_time=time(13, 0),
            status=HallReservationModel.Status.PENDING,
        )
        baker.make(
            HallReservationModel,
            reservation_date=tomorrow,
            start_time=time(14, 0),
            end_time=time(15, 0),
            status=HallReservationModel.Status.PENDING,
        )
        # 2 news
        baker.make(SunnyValeNewsModel, _quantity=2)

        self.authenticate(self.admin)
        response = self.client.get(URL)

        self.assertEqual(response.status_code, 200, response.data)
        # admin + user_a + user_b -> 3 active users
        self.assertEqual(response.data["active_residents"], 3)
        # 1 BBQ approved + 1 Hall approved
        self.assertEqual(response.data["total_reservations"], 2)
        # 1 BBQ pending + 2 Hall pending
        self.assertEqual(response.data["pending_reservations"], 3)
        self.assertEqual(response.data["pending_bbq_reservations"], 1)
        self.assertEqual(response.data["pending_hall_reservations"], 2)
        self.assertEqual(response.data["published_news"], 2)

    def test_admin_overview_zeros_when_empty(self):
        self.authenticate(self.admin)
        response = self.client.get(URL)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["total_reservations"], 0)
        self.assertEqual(response.data["pending_reservations"], 0)
        self.assertEqual(response.data["pending_bbq_reservations"], 0)
        self.assertEqual(response.data["pending_hall_reservations"], 0)
        self.assertEqual(response.data["published_news"], 0)

    def test_overview_response_is_cached_for_subsequent_requests(self):
        self.authenticate(self.admin)
        first = self.client.get(URL)
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(first.data["published_news"], 0)

        # New news created AFTER the first call: cache should still hold
        # the stale value within the 1h TTL window.
        baker.make(SunnyValeNewsModel, _quantity=3)

        second = self.client.get(URL)
        self.assertEqual(second.status_code, 200, second.data)
        self.assertEqual(second.data["published_news"], 0)
