"""Smoke tests for the service requests API."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

from service_requests.models import ServiceRequestModel
from tests_base.base_tests_user import BaseTestsUsers


pytestmark = pytest.mark.api


LIST_URL = reverse("service_requests:service_requests_list_and_create")


def detail_url(pk):
    return reverse(
        "service_requests:service_request_detail_retrieve_and_delete",
        kwargs={"pk": pk},
    )


def accept_url(pk, action):
    return reverse(
        "service_requests:accept_request",
        kwargs={"pk": pk, "accept_or_decline": action},
    )


class ServiceRequestsAPISmoke(BaseTestsUsers):
    def test_anonymous_blocked(self):
        self.assertEqual(self.client.get(LIST_URL).status_code, 401)

    def test_user_creates(self):
        self.authenticate(self.user_a)
        response = self.client.post(
            LIST_URL,
            data={
                "requester_user": self.user_a.id,
                "title": "Fix",
                "request_scheduled_date": (timezone.now() + timedelta(days=1)).isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)

    def test_user_cannot_read_others(self):
        item = baker.make(ServiceRequestModel, requester_user=self.user_b)
        self.authenticate(self.user_a)
        self.assertEqual(self.client.get(detail_url(item.id)).status_code, 404)

    def test_admin_can_accept(self):
        item = baker.make(ServiceRequestModel, requester_user=self.user_a)
        self.authenticate(self.admin)
        response = self.client.patch(accept_url(item.id, "accept"), data={}, format="json")
        self.assertEqual(response.status_code, 200, response.data)

    def test_admin_invalid_action_400(self):
        item = baker.make(ServiceRequestModel, requester_user=self.user_a)
        self.authenticate(self.admin)
        response = self.client.patch(accept_url(item.id, "wat"), data={}, format="json")
        self.assertEqual(response.status_code, 400)
