from datetime import datetime, timedelta, timezone as dt_tz

from django.urls import reverse
from model_bakery import baker

from service_requests.models import ServiceRequestModel
from tests_base.base_tests_user import BaseTestsUsers


LIST_URL = reverse("service_requests:service_requests_list_and_create")


def detail_url(pk: int) -> str:
    return reverse(
        "service_requests:service_request_detail_retrieve_and_delete",
        kwargs={"pk": pk},
    )


def accept_url(pk: int, action: str) -> str:
    return reverse(
        "service_requests:accept_request",
        kwargs={"pk": pk, "accept_or_decline": action},
    )


def _future_iso() -> str:
    return (
        datetime.now(dt_tz.utc) + timedelta(days=2)
    ).isoformat().replace("+00:00", "Z")


class ServiceRequestListTests(BaseTestsUsers):
    def test_anonymous_blocked(self):
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 401)

    def test_user_sees_only_own_requests(self):
        own = baker.make(ServiceRequestModel, requester_user=self.user_a)
        baker.make(ServiceRequestModel, requester_user=self.user_b)
        self.authenticate(self.user_a)
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        ids = [item["id"] for item in response.data]
        self.assertIn(own.id, ids)
        self.assertEqual(len(response.data), 1)

    def test_admin_sees_everything(self):
        baker.make(ServiceRequestModel, requester_user=self.user_a)
        baker.make(ServiceRequestModel, requester_user=self.user_b)
        self.authenticate(self.admin)
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data), 2)


class ServiceRequestCreateTests(BaseTestsUsers):
    def _payload(self, **overrides):
        data = {
            "requester_user": self.user_a.id,
            "title": "Broken light",
            "request_description": "Hallway light is out",
            "service_type": "Maintenance",
            "location": "Tower A",
            "priority": "high",
            "request_scheduled_date": _future_iso(),
        }
        data.update(overrides)
        return data

    def test_creates_request(self):
        self.authenticate(self.user_a)
        response = self.client.post(LIST_URL, data=self._payload(), format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(
            ServiceRequestModel.objects.filter(title="Broken light").exists()
        )

    def test_invalid_payload_returns_400(self):
        self.authenticate(self.user_a)
        response = self.client.post(
            LIST_URL, data={"title": ""}, format="json"
        )
        self.assertEqual(response.status_code, 400)


class ServiceRequestDetailTests(BaseTestsUsers):
    def setUp(self):
        super().setUp()
        self.obj = baker.make(ServiceRequestModel, requester_user=self.user_a)

    def test_owner_can_retrieve(self):
        self.authenticate(self.user_a)
        response = self.client.get(detail_url(self.obj.id))
        self.assertEqual(response.status_code, 200)

    def test_other_user_gets_404(self):
        self.authenticate(self.user_b)
        response = self.client.get(detail_url(self.obj.id))
        self.assertEqual(response.status_code, 404)

    def test_admin_can_retrieve(self):
        self.authenticate(self.admin)
        response = self.client.get(detail_url(self.obj.id))
        self.assertEqual(response.status_code, 200)

    def test_owner_can_patch(self):
        self.authenticate(self.user_a)
        response = self.client.patch(
            detail_url(self.obj.id), data={"title": "New title"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.title, "New title")

    def test_owner_can_delete(self):
        self.authenticate(self.user_a)
        response = self.client.delete(detail_url(self.obj.id))
        self.assertEqual(response.status_code, 204)
        self.assertFalse(
            ServiceRequestModel.objects.filter(pk=self.obj.id).exists()
        )

    def test_unrelated_user_cannot_delete(self):
        self.authenticate(self.user_b)
        response = self.client.delete(detail_url(self.obj.id))
        self.assertEqual(response.status_code, 404)


class ServiceRequestAcceptDeclineTests(BaseTestsUsers):
    def setUp(self):
        super().setUp()
        self.obj = baker.make(ServiceRequestModel, requester_user=self.user_a)

    def test_non_admin_blocked(self):
        self.authenticate(self.user_a)
        response = self.client.patch(accept_url(self.obj.id, "accept"))
        self.assertEqual(response.status_code, 403)

    def test_admin_accepts(self):
        self.authenticate(self.admin)
        response = self.client.patch(
            accept_url(self.obj.id, "accept"),
            data={"responsable_staff": "admin", "more_details": "approved"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.status, "accepted")

    def test_admin_declines(self):
        self.authenticate(self.admin)
        response = self.client.patch(
            accept_url(self.obj.id, "decline"),
            data={"more_details": "rejected"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.status, "declined")

    def test_invalid_action_returns_400(self):
        self.authenticate(self.admin)
        response = self.client.patch(accept_url(self.obj.id, "bogus"))
        self.assertEqual(response.status_code, 400)
