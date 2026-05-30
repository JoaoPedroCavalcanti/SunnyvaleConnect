from datetime import timedelta
from unittest.mock import patch

from django.urls import reverse, NoReverseMatch
from django.utils import timezone
from model_bakery import baker

from sunnyValeConnect.utils.mixing_and_unmixing_strings import mix_strings
from sunnyValeConnect.utils.settings_config import secret_mixin_string
from tests_base.base_tests_user import BaseTestsUsers
from visitor_access.models import VisitorAccessModel


def _list_url() -> str:
    try:
        return reverse("visitor_access-router-list")
    except NoReverseMatch:
        return "/visitor_access/"


def _detail_url(pk: int) -> str:
    try:
        return reverse("visitor_access-router-detail", kwargs={"pk": pk})
    except NoReverseMatch:
        return f"/visitor_access/{pk}/"


def _checkin_url(link: str) -> str:
    try:
        return reverse(
            "visitor_access-router-checkin",
            kwargs={"visitor_access_link_checkin": link},
        )
    except NoReverseMatch:
        return f"/visitor_access/checkin/{link}/"


def _checkout_url(link: str) -> str:
    try:
        return reverse(
            "visitor_access-router-checkout",
            kwargs={"visitor_access_link_checkout": link},
        )
    except NoReverseMatch:
        return f"/visitor_access/checkout/{link}/"


LIST_URL = _list_url()


def _future_iso(days: int = 2) -> str:
    return (timezone.now() + timedelta(days=days)).isoformat()


class VisitorAccessPermissionTests(BaseTestsUsers):
    def test_anonymous_blocked_on_list(self):
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 401)

    def test_user_only_sees_own_records(self):
        baker.make(VisitorAccessModel, host_user=self.user_a, _quantity=2)
        baker.make(VisitorAccessModel, host_user=self.user_b, _quantity=3)
        self.authenticate(self.user_a)
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)


class VisitorAccessCreateTests(BaseTestsUsers):
    def _payload(self, **overrides):
        data = {
            "visitor_name": "John Doe",
            "email": "visitor@example.com",
            "scheduled_date": _future_iso(),
        }
        data.update(overrides)
        return data

    def test_regular_user_creates_for_self(self):
        self.authenticate(self.user_a)
        response = self.client.post(LIST_URL, data=self._payload(), format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["host_user"], self.user_a.id)
        # Link checkin generated
        self.assertIsNotNone(response.data["link_checkin"])

    def test_regular_user_cannot_pass_host_user(self):
        self.authenticate(self.user_a)
        response = self.client.post(
            LIST_URL,
            data=self._payload(host_user=self.user_b.id),
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_admin_must_pass_host_user(self):
        self.authenticate(self.admin)
        response = self.client.post(LIST_URL, data=self._payload(), format="json")
        self.assertEqual(response.status_code, 400)

    def test_admin_creates_for_other_user(self):
        self.authenticate(self.admin)
        response = self.client.post(
            LIST_URL,
            data=self._payload(host_user=self.user_a.id),
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)

    def test_cannot_create_with_past_date(self):
        self.authenticate(self.user_a)
        past = (timezone.now() - timedelta(days=1)).isoformat()
        response = self.client.post(
            LIST_URL, data=self._payload(scheduled_date=past), format="json"
        )
        self.assertEqual(response.status_code, 400)


class VisitorAccessDeleteTests(BaseTestsUsers):
    def test_cannot_delete_past_visitor_access(self):
        obj = baker.make(
            VisitorAccessModel,
            host_user=self.user_a,
            scheduled_date=timezone.now() - timedelta(days=1),
        )
        self.authenticate(self.user_a)
        response = self.client.delete(_detail_url(obj.id))
        self.assertEqual(response.status_code, 400)

    def test_can_delete_future_visitor_access(self):
        obj = baker.make(
            VisitorAccessModel,
            host_user=self.user_a,
            scheduled_date=timezone.now() + timedelta(days=1),
        )
        self.authenticate(self.user_a)
        response = self.client.delete(_detail_url(obj.id))
        self.assertEqual(response.status_code, 204)


class VisitorAccessCheckinCheckoutTests(BaseTestsUsers):
    """Tests the public check-in / check-out endpoints."""

    def _build_link(self, obj_id: int) -> str:
        return mix_strings(string=str(obj_id), mix_code=secret_mixin_string)

    def test_checkin_succeeds_during_window(self):
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
        link = self._build_link(obj.id)
        response = self.client.get(_checkin_url(link))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("checkin_code", response.data)
        obj.refresh_from_db()
        self.assertEqual(obj.status, "Checked-in")
        self.assertNotEqual(obj.checkin_code, "")

    def test_checkin_outside_window_returns_text(self):
        obj = baker.make(
            VisitorAccessModel,
            host_user=self.user_a,
            email="v@example.com",
            visitor_name="Guest",
            checkin_code="",
            checkout_code="",
            status="Scheduled",
            scheduled_date=timezone.now() + timedelta(days=1),
            checkin_date_time=timezone.now() + timedelta(days=1),
            checkout_date_time=timezone.now() + timedelta(days=1, hours=2),
        )
        link = self._build_link(obj.id)
        response = self.client.get(_checkin_url(link))
        self.assertEqual(response.status_code, 200)
        self.assertIn("scheduled time", str(response.data))

    def test_checkout_blocked_if_not_checked_in(self):
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
        link = self._build_link(obj.id)
        response = self.client.get(_checkout_url(link))
        self.assertEqual(response.status_code, 400)

    def test_checkout_succeeds_after_checkin(self):
        obj = baker.make(
            VisitorAccessModel,
            host_user=self.user_a,
            email="v@example.com",
            visitor_name="Guest",
            checkin_code="12345",
            checkout_code="",
            status="Checked-in",
            scheduled_date=timezone.now() + timedelta(hours=2),
            checkin_date_time=timezone.now() - timedelta(minutes=5),
            checkout_date_time=timezone.now() + timedelta(hours=3),
        )
        link = self._build_link(obj.id)
        response = self.client.get(_checkout_url(link))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("checkout_code", response.data)
        obj.refresh_from_db()
        self.assertEqual(obj.status, "Checked-out")
