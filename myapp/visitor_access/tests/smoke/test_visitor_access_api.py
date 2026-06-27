"""Smoke tests for the visitor access API."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

from tests_base.base_tests_user import BaseTestsUsers
from users.models import EmployeeType, UserRole
from visitor_access.models import VisitorAccessModel


pytestmark = pytest.mark.api


LIST_URL = reverse("visitor_access:list-create")
VALIDATE_URL = reverse("visitor_access:validate")


def detail_url(pk):
    return reverse("visitor_access:detail", kwargs={"pk": pk})


class VisitorAccessAPISmoke(BaseTestsUsers):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.doorman = cls.User.objects.create_user(
            username="doorman",
            email="doorman@example.com",
            password="Abcd123!",
            full_name="Doorman User",
            birth_date=cls.admin.birth_date,
            cpf="52998224725",
            phone="11988887777",
            apartment="0",
            role=UserRole.EMPLOYEE,
            employee_types=[EmployeeType.DOORMAN],
        )

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
        self.assertEqual(response.data["host"]["id"], self.user_a.id)
        self.assertFalse(response.data["qr_access_enabled"])

    def test_user_creates_with_qr_access(self):
        self.authenticate(self.user_a)
        response = self.client.post(
            LIST_URL,
            data={
                "visitor_name": "John",
                "email": "v@example.com",
                "scheduled_date": self._future(),
                "qr_access_enabled": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(response.data["qr_access_enabled"])
        obj = VisitorAccessModel.objects.get(id=response.data["id"])
        self.assertTrue(obj.access_token)
        self.assertTrue(obj.access_code)

    def test_qr_access_without_email_rejected(self):
        self.authenticate(self.user_a)
        response = self.client.post(
            LIST_URL,
            data={
                "visitor_name": "John",
                "email": "",
                "scheduled_date": self._future(),
                "qr_access_enabled": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)

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

    def test_doorman_validates_access_code(self):
        obj = baker.make(
            VisitorAccessModel,
            host_user=self.user_a,
            email="v@example.com",
            visitor_name="Guest",
            checkin_code="",
            checkout_code="",
            status=VisitorAccessModel.Status.SCHEDULED,
            qr_access_enabled=True,
            access_token="token-abc",
            access_code="A1B2C",
            scheduled_date=timezone.now() - timedelta(minutes=5),
            checkin_date_time=timezone.now() - timedelta(minutes=5),
            checkout_date_time=timezone.now() + timedelta(hours=2),
        )
        self.authenticate(self.doorman)
        response = self.client.post(
            VALIDATE_URL,
            data={"credential": "A1B2C"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["status"], "CHECKED_IN")
        obj.refresh_from_db()
        self.assertEqual(obj.status, VisitorAccessModel.Status.CHECKED_IN)

    def test_resident_cannot_validate(self):
        obj = baker.make(
            VisitorAccessModel,
            host_user=self.user_a,
            qr_access_enabled=True,
            access_code="Z9Y8X",
            status=VisitorAccessModel.Status.SCHEDULED,
            scheduled_date=timezone.now() + timedelta(days=1),
            checkin_date_time=timezone.now() - timedelta(minutes=5),
            checkout_date_time=timezone.now() + timedelta(hours=2),
        )
        self.authenticate(self.user_a)
        response = self.client.post(
            VALIDATE_URL,
            data={"credential": obj.access_code},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_cannot_cancel_past(self):
        obj = baker.make(
            VisitorAccessModel,
            host_user=self.user_a,
            scheduled_date=timezone.now() - timedelta(days=1),
            status=VisitorAccessModel.Status.SCHEDULED,
        )
        self.authenticate(self.user_a)
        self.assertEqual(self.client.delete(detail_url(obj.id)).status_code, 400)

    def test_delete_soft_cancels_future_visit(self):
        obj = baker.make(
            VisitorAccessModel,
            host_user=self.user_a,
            scheduled_date=timezone.now() + timedelta(days=2),
            status=VisitorAccessModel.Status.SCHEDULED,
        )
        self.authenticate(self.user_a)
        response = self.client.delete(detail_url(obj.id))
        self.assertEqual(response.status_code, 204)
        obj.refresh_from_db()
        self.assertEqual(obj.status, VisitorAccessModel.Status.CANCELLED)

    def test_list_filters_by_period_future(self):
        future = baker.make(
            VisitorAccessModel,
            host_user=self.user_a,
            scheduled_date=timezone.now() + timedelta(days=2),
            status=VisitorAccessModel.Status.SCHEDULED,
        )
        baker.make(
            VisitorAccessModel,
            host_user=self.user_a,
            scheduled_date=timezone.now() - timedelta(days=2),
            status=VisitorAccessModel.Status.CHECKED_OUT,
        )
        self.authenticate(self.user_a)
        response = self.client.get(LIST_URL + "?period=future")
        self.assertEqual(response.status_code, 200)
        ids = {row["id"] for row in response.data["results"]}
        self.assertEqual(ids, {future.id})

    def test_list_filters_by_status_no_show(self):
        no_show = baker.make(
            VisitorAccessModel,
            host_user=self.user_a,
            scheduled_date=timezone.now() - timedelta(days=1),
            status=VisitorAccessModel.Status.SCHEDULED,
        )
        baker.make(
            VisitorAccessModel,
            host_user=self.user_a,
            scheduled_date=timezone.now() + timedelta(days=1),
            status=VisitorAccessModel.Status.SCHEDULED,
        )
        self.authenticate(self.user_a)
        response = self.client.get(LIST_URL + "?status=NO_SHOW")
        self.assertEqual(response.status_code, 200)
        ids = {row["id"] for row in response.data["results"]}
        self.assertEqual(ids, {no_show.id})
        row = response.data["results"][0]
        self.assertEqual(row["status"], "NO_SHOW")

    def test_list_invalid_status_returns_400(self):
        self.authenticate(self.user_a)
        response = self.client.get(LIST_URL + "?status=BANANA")
        self.assertEqual(response.status_code, 400)

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

    def test_all_day_today_lists_as_future_with_scheduled_status(self):
        earlier_today = timezone.localtime().replace(
            hour=1, minute=0, second=0, microsecond=0
        )
        visit = baker.make(
            VisitorAccessModel,
            host_user=self.user_a,
            visitor_name="All Day Guest",
            scheduled_date=earlier_today,
            checkin_date_time=earlier_today,
            checkout_date_time=earlier_today.replace(
                hour=23, minute=59, second=59, microsecond=0
            ),
            all_day=True,
            status=VisitorAccessModel.Status.SCHEDULED,
        )
        self.authenticate(self.user_a)
        future = self.client.get(LIST_URL + "?period=future")
        self.assertEqual(future.status_code, 200)
        self.assertIn(visit.id, {row["id"] for row in future.data["results"]})
        row = next(r for r in future.data["results"] if r["id"] == visit.id)
        self.assertEqual(row["status"], "SCHEDULED")
