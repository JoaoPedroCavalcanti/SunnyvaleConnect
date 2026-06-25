"""Smoke tests for employee dashboard API."""

from datetime import date, timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from households.models import Household
from delivery_notification.models import DeliveryNotificationModel
from service_requests.models import ServiceRequestModel
from tests_base.base_tests_user import BaseTestsUsers, _gen_cpf
from visitor_access.models import VisitorAccessModel


pytestmark = pytest.mark.api


DAY_SUMMARY_URL = reverse("employee_dashboard:day-summary")
UPCOMING_URL = reverse("employee_dashboard:upcoming-visits")


class EmployeeDashboardAPISmoke(BaseTestsUsers):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.doorman = cls.User.objects.create_user(
            username="porteiro",
            email="porteiro@example.com",
            password="Abcd123!",
            full_name="Porteiro",
            birth_date=date(1985, 1, 1),
            cpf=_gen_cpf(),
            phone="11988887777",
            role="EMPLOYEE",
            employee_types=["DOORMAN"],
        )
        cls.cleaner = cls.User.objects.create_user(
            username="zelador",
            email="zelador@example.com",
            password="Abcd123!",
            full_name="Zelador",
            birth_date=date(1985, 6, 1),
            cpf=_gen_cpf(),
            phone="11977776666",
            role="EMPLOYEE",
            employee_types=["CLEANING"],
        )

    def test_resident_forbidden(self):
        self.authenticate(self.user_a)
        self.assertEqual(self.client.get(DAY_SUMMARY_URL).status_code, 403)

    def test_doorman_day_summary(self):
        household = Household.objects.create(
            apartment=self.user_a.apartment,
            block=self.user_a.block,
            status=Household.Status.ACTIVE,
        )
        DeliveryNotificationModel.objects.create(
            household=household,
            delivery_platform="other",
        )
        now = timezone.now()
        VisitorAccessModel.objects.create(
            visitor_name="Guest",
            host_user=self.user_a,
            email="g@x.com",
            scheduled_date=now + timedelta(hours=2),
            checkin_date_time=now + timedelta(hours=2),
            checkout_date_time=now + timedelta(hours=5),
            checkin_code="",
            checkout_code="",
            status=VisitorAccessModel.Status.SCHEDULED,
        )
        ServiceRequestModel.objects.create(
            requester=self.user_a,
            title="Leak",
        )
        self.authenticate(self.doorman)
        response = self.client.get(DAY_SUMMARY_URL)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["deliveries_today"], 1)
        self.assertEqual(response.data["visits_today"], 1)
        self.assertEqual(response.data["scheduled_visits"], 1)
        self.assertIsNone(response.data["pending_service_requests"])

    def test_cleaner_day_summary(self):
        ServiceRequestModel.objects.create(
            requester=self.user_a,
            title="Clean pool",
        )
        self.authenticate(self.cleaner)
        response = self.client.get(DAY_SUMMARY_URL)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIsNone(response.data["deliveries_today"])
        self.assertIsNone(response.data["visits_today"])
        self.assertEqual(response.data["pending_service_requests"], 1)

    def test_doorman_upcoming_visits(self):
        now = timezone.now()
        VisitorAccessModel.objects.create(
            visitor_name="Maria",
            host_user=self.user_a,
            email="m@x.com",
            scheduled_date=now + timedelta(hours=1),
            checkin_date_time=now + timedelta(hours=1),
            checkout_date_time=now + timedelta(hours=4),
            checkin_code="",
            checkout_code="",
            description="Manutenção",
        )
        self.authenticate(self.doorman)
        response = self.client.get(UPCOMING_URL)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["visitor_name"], "Maria")
        self.assertEqual(response.data[0]["host"]["apartment"], self.user_a.apartment)

    def test_cleaner_cannot_list_upcoming_visits(self):
        self.authenticate(self.cleaner)
        self.assertEqual(self.client.get(UPCOMING_URL).status_code, 403)
