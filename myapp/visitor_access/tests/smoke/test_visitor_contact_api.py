"""Smoke tests for the visitor contact API."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from tests_base.base_tests_user import BaseTestsUsers
from visitor_access.models import VisitorAccessModel, VisitorContactModel


pytestmark = pytest.mark.api


LIST_URL = reverse("visitor_access:contacts-list-create")


def detail_url(pk):
    return reverse("visitor_access:contacts-detail", kwargs={"pk": pk})


def schedule_url(pk):
    return reverse("visitor_access:contacts-schedule", kwargs={"pk": pk})


class VisitorContactAPISmoke(BaseTestsUsers):
    def _future(self, days=2):
        return (timezone.now() + timedelta(days=days)).isoformat()

    def test_anonymous_blocked(self):
        self.assertEqual(self.client.get(LIST_URL).status_code, 401)

    def test_user_creates_and_lists_own_contacts(self):
        VisitorContactModel.objects.create(
            host_user=self.user_b, name="Theirs", email="t@x.com"
        )
        self.authenticate(self.user_a)
        create = self.client.post(
            LIST_URL,
            data={"name": "João", "email": "joao@example.com"},
            format="json",
        )
        self.assertEqual(create.status_code, 201, create.data)
        self.assertEqual(create.data["host_user"], self.user_a.id)

        listing = self.client.get(LIST_URL)
        self.assertEqual(listing.status_code, 200)
        names = [c["name"] for c in listing.data["results"]]
        self.assertIn("João", names)
        self.assertNotIn("Theirs", names)

    def test_duplicate_name_rejected(self):
        VisitorContactModel.objects.create(host_user=self.user_a, name="João")
        self.authenticate(self.user_a)
        response = self.client.post(
            LIST_URL,
            data={"name": "joão"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_patch_and_delete(self):
        contact = VisitorContactModel.objects.create(
            host_user=self.user_a, name="João", email="old@x.com"
        )
        self.authenticate(self.user_a)
        patch = self.client.patch(
            detail_url(contact.id),
            data={"name": "João Silva", "email": "new@x.com"},
            format="json",
        )
        self.assertEqual(patch.status_code, 200, patch.data)
        self.assertEqual(patch.data["name"], "João Silva")

        delete = self.client.delete(detail_url(contact.id))
        self.assertEqual(delete.status_code, 204)
        self.assertFalse(
            VisitorContactModel.objects.filter(id=contact.id).exists()
        )

    def test_schedule_creates_solo_visit(self):
        contact = VisitorContactModel.objects.create(
            host_user=self.user_a, name="João", email="joao@example.com"
        )
        self.authenticate(self.user_a)
        response = self.client.post(
            schedule_url(contact.id),
            data={"scheduled_date": self._future(), "all_day": False},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["visitor_name"], "João")
        self.assertFalse(response.data["is_group"])
        self.assertTrue(
            VisitorAccessModel.objects.filter(
                host_user=self.user_a, visitor_name="João"
            ).exists()
        )

    def test_other_user_cannot_access(self):
        contact = VisitorContactModel.objects.create(
            host_user=self.user_a, name="Mine"
        )
        self.authenticate(self.user_b)
        self.assertEqual(self.client.get(detail_url(contact.id)).status_code, 404)
