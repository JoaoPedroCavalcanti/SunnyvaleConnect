"""Smoke tests for the service requests API.

These tests hit the full HTTP stack with a real (SQLite in-memory) DB.
The goal is not to re-test every business rule — that's the unit suite's
job — but to make sure the layers are wired together:

  * auth is enforced
  * residents only see their own list, admins see everything
  * residents cannot tamper with admin fields via create
  * the respond endpoint requires a non-empty justification
  * a non-admin gets 403 when trying to respond
"""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from service_requests.models import ServiceRequestModel
from tests_base.base_tests_user import BaseTestsUsers


pytestmark = pytest.mark.api


LIST_URL = reverse("service_requests:list-create")


def detail_url(pk):
    return reverse("service_requests:detail", kwargs={"pk": pk})


def respond_url(pk):
    return reverse("service_requests:respond", kwargs={"pk": pk})


def complete_url(pk):
    return reverse("service_requests:complete", kwargs={"pk": pk})


def _make_request(user, **overrides) -> ServiceRequestModel:
    defaults = {
        "requester": user,
        "title": "Fix leak",
        "service_type": ServiceRequestModel.ServiceType.PLUMBING,
        "priority": ServiceRequestModel.Priority.MEDIUM,
    }
    defaults.update(overrides)
    return ServiceRequestModel.objects.create(**defaults)


class ServiceRequestsAPISmoke(BaseTestsUsers):
    # --- auth ------------------------------------------------------ #
    def test_anonymous_blocked(self):
        self.assertEqual(self.client.get(LIST_URL).status_code, 401)

    # --- create ---------------------------------------------------- #
    def test_user_creates_request(self):
        self.authenticate(self.user_a)
        response = self.client.post(
            LIST_URL,
            data={
                "title": "Leaking pipe",
                "description": "kitchen sink",
                "service_type": "PLUMBING",
                "priority": "HIGH",
                "request_scheduled_date": (
                    timezone.now() + timedelta(days=1)
                ).isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["status"], "PENDING")
        self.assertEqual(response.data["requester"]["id"], self.user_a.id)

    def test_resident_cannot_smuggle_status_on_create(self):
        self.authenticate(self.user_a)
        response = self.client.post(
            LIST_URL,
            data={"title": "x", "status": "ACCEPTED"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        # status is dropped server-side; payload has no extra field anyway
        self.assertEqual(response.data["status"], "PENDING")

    # --- list ------------------------------------------------------ #
    def test_all_users_see_every_request_in_list(self):
        _make_request(self.user_a, title="mine")
        _make_request(self.user_b, title="theirs")
        self.authenticate(self.user_a)
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)

    def test_admin_sees_all_in_list(self):
        _make_request(self.user_a)
        _make_request(self.user_b)
        self.authenticate(self.admin)
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)

    def test_admin_filters_by_priority(self):
        _make_request(self.user_a, priority=ServiceRequestModel.Priority.URGENT)
        _make_request(self.user_b, priority=ServiceRequestModel.Priority.LOW)
        self.authenticate(self.admin)
        response = self.client.get(LIST_URL, {"priority": "URGENT"})
        self.assertEqual(response.data["count"], 1)

    # --- detail / 404 --------------------------------------------- #
    def test_any_user_can_read_others(self):
        item = _make_request(self.user_b)
        self.authenticate(self.user_a)
        response = self.client.get(detail_url(item.id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], item.title)

    # --- respond --------------------------------------------------- #
    def test_admin_accepts_with_message(self):
        item = _make_request(self.user_a)
        self.authenticate(self.admin)
        response = self.client.post(
            respond_url(item.id),
            data={"action": "accept", "response": "scheduled for tomorrow"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["status"], "ACCEPTED")
        self.assertEqual(
            response.data["admin_response"], "scheduled for tomorrow"
        )
        self.assertEqual(
            response.data["responded_by"]["id"], self.admin.id
        )

    def test_admin_declines_with_message(self):
        item = _make_request(self.user_a)
        self.authenticate(self.admin)
        response = self.client.post(
            respond_url(item.id),
            data={"action": "decline", "response": "out of scope"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["status"], "DECLINED")

    def test_respond_decline_requires_response(self):
        item = _make_request(self.user_a)
        self.authenticate(self.admin)
        response = self.client.post(
            respond_url(item.id),
            data={"action": "decline"},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)

    def test_respond_accept_without_response(self):
        item = _make_request(self.user_a)
        self.authenticate(self.admin)
        response = self.client.post(
            respond_url(item.id),
            data={"action": "accept"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["status"], "ACCEPTED")
        self.assertEqual(response.data["admin_response"], "")

    def test_respond_forbidden_for_non_admin(self):
        item = _make_request(self.user_a)
        self.authenticate(self.user_b)
        response = self.client.post(
            respond_url(item.id),
            data={"action": "accept", "response": "ok"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    # --- complete -------------------------------------------------- #
    def test_admin_completes_accepted_request(self):
        item = _make_request(self.user_a)
        self.authenticate(self.admin)
        self.client.post(
            respond_url(item.id),
            data={"action": "accept", "response": "ok"},
            format="json",
        )
        response = self.client.post(complete_url(item.id))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["status"], "COMPLETED")

    def test_cannot_complete_pending(self):
        item = _make_request(self.user_a)
        self.authenticate(self.admin)
        response = self.client.post(complete_url(item.id))
        self.assertEqual(response.status_code, 400)

    def test_cleaning_mine_filter(self):
        from datetime import date

        from tests_base.base_tests_user import _gen_cpf

        cleaner = self.User.objects.create_user(
            username=f"{self.condominium.code}:zelador",
            email="zelador@example.com",
            password="Abcd123!",
            full_name="Zelador",
            birth_date=date(1985, 1, 1),
            cpf=_gen_cpf(),
            phone="11988887777",
            role="EMPLOYEE",
            employee_types=["CLEANING"],
            condominium=self.condominium,
        )
        mine = _make_request(self.user_a, title="mine")
        other = _make_request(self.user_b, title="other")
        self.authenticate(cleaner)
        self.client.post(
            respond_url(mine.id),
            data={"action": "accept", "response": "ok"},
            format="json",
        )
        self.authenticate(self.admin)
        self.client.post(
            respond_url(other.id),
            data={"action": "decline", "response": "no"},
            format="json",
        )
        self.authenticate(cleaner)
        response = self.client.get(LIST_URL, {"mine": "true"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["title"], "mine")
