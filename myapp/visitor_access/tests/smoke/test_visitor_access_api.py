"""Smoke tests for the visitor access API."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

from shared.container import container
from shared.test_doubles.fakes import FakeStringMixer
from tests_base.base_tests_user import BaseTestsUsers
from visitor_access.models import VisitorAccessModel


pytestmark = pytest.mark.api


LIST_URL = reverse("visitor_access:list-create")


def detail_url(pk):
    return reverse("visitor_access:detail", kwargs={"pk": pk})


def checkin_url(link):
    return reverse(
        "visitor_access:checkin", kwargs={"visitor_access_link_checkin": link}
    )


def checkout_url(link):
    return reverse(
        "visitor_access:checkout", kwargs={"visitor_access_link_checkout": link}
    )


class VisitorAccessAPISmoke(BaseTestsUsers):
    def setUp(self):
        super().setUp()
        # use identity mixer for predictable links
        container.override("string_mixer", FakeStringMixer())

    def tearDown(self):
        container.reset()

    def _future(self, days=2):
        return (timezone.now() + timedelta(days=days)).isoformat()

    def test_anonymous_blocked_on_list(self):
        self.assertEqual(self.client.get(LIST_URL).status_code, 401)

    def test_user_creates_for_self(self):
        self.authenticate(self.user_a)
        response = self.client.post(
            LIST_URL,
            data={
                "visitor_name": "John",
                "email": "v@example.com",
                "scheduled_date": self._future(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["host_user"], self.user_a.id)

    def test_past_date_rejected(self):
        self.authenticate(self.user_a)
        response = self.client.post(
            LIST_URL,
            data={
                "visitor_name": "John",
                "email": "v@example.com",
                "scheduled_date": (timezone.now() - timedelta(days=1)).isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_checkin_inside_window(self):
        obj = baker.make(
            VisitorAccessModel,
            host_user=self.user_a,
            email="v@example.com",
            visitor_name="Guest",
            checkin_code="",
            checkout_code="",
            status="Scheduled",
            scheduled_date=timezone.now() - timedelta(minutes=5),
            checkin_date_time=timezone.now() - timedelta(minutes=5),
            checkout_date_time=timezone.now() + timedelta(hours=2),
        )
        response = self.client.get(checkin_url(str(obj.id)))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("checkin_code", response.data)

    def test_checkout_blocked_if_still_scheduled(self):
        obj = baker.make(
            VisitorAccessModel,
            host_user=self.user_a,
            email="v@example.com",
            visitor_name="Guest",
            checkin_code="",
            checkout_code="",
            status="Scheduled",
            scheduled_date=timezone.now() + timedelta(hours=2),
            checkin_date_time=timezone.now() + timedelta(hours=2),
            checkout_date_time=timezone.now() + timedelta(hours=5),
        )
        response = self.client.get(checkout_url(str(obj.id)))
        self.assertEqual(response.status_code, 400)

    def test_cannot_delete_past(self):
        obj = baker.make(
            VisitorAccessModel,
            host_user=self.user_a,
            scheduled_date=timezone.now() - timedelta(days=1),
        )
        self.authenticate(self.user_a)
        self.assertEqual(self.client.delete(detail_url(obj.id)).status_code, 400)

    def test_all_day_visit_covers_full_day(self):
        self.authenticate(self.user_a)
        response = self.client.post(
            LIST_URL,
            data={
                "visitor_name": "John",
                "email": "v@example.com",
                "scheduled_date": self._future(),
                "all_day": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(response.data["all_day"])
        obj = VisitorAccessModel.objects.get(id=response.data["id"])
        local_in = timezone.localtime(obj.checkin_date_time)
        local_out = timezone.localtime(obj.checkout_date_time)
        self.assertEqual(local_in.hour, 0)
        self.assertEqual(local_in.minute, 0)
        self.assertEqual(local_out.hour, 23)
        self.assertEqual(local_out.minute, 59)
