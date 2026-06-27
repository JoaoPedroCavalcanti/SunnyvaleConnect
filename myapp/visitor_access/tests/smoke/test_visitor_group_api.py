"""Smoke tests for the visitor group API."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from tests_base.base_tests_user import BaseTestsUsers
from visitor_access.models import VisitorAccessModel, VisitorGroupModel


pytestmark = pytest.mark.api


LIST_URL = reverse("visitor_access:groups-list-create")


def detail_url(pk):
    return reverse("visitor_access:groups-detail", kwargs={"pk": pk})


def schedule_url(pk):
    return reverse("visitor_access:groups-schedule", kwargs={"pk": pk})


GROUP_VISITS_LIST_URL = reverse("visitor_access:groups-visits-list")
SOLO_VISITS_LIST_URL = reverse("visitor_access:list-create")


class VisitorGroupAPISmoke(BaseTestsUsers):
    def _future(self, days=2):
        return (timezone.now() + timedelta(days=days)).isoformat()

    # ------------------------------------------------------------------ #
    # auth                                                               #
    # ------------------------------------------------------------------ #
    def test_anonymous_blocked(self):
        self.assertEqual(self.client.get(LIST_URL).status_code, 401)

    # ------------------------------------------------------------------ #
    # create / list                                                      #
    # ------------------------------------------------------------------ #
    def test_user_creates_group_with_members(self):
        self.authenticate(self.user_a)
        response = self.client.post(
            LIST_URL,
            data={
                "name": "Família Pai",
                "members": [
                    {"name": "João", "email": "joao@example.com"},
                    {"name": "Maria", "email": "maria@example.com"},
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["host_user"], self.user_a.id)
        self.assertEqual(len(response.data["members"]), 2)

    def test_user_only_sees_own_groups(self):
        VisitorGroupModel.objects.create(host_user=self.user_a, name="Mine")
        VisitorGroupModel.objects.create(host_user=self.user_b, name="Theirs")
        self.authenticate(self.user_a)
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        names = [g["name"] for g in response.data["results"]]
        self.assertIn("Mine", names)
        self.assertNotIn("Theirs", names)

    def test_duplicate_name_rejected(self):
        VisitorGroupModel.objects.create(host_user=self.user_a, name="Família Pai")
        self.authenticate(self.user_a)
        response = self.client.post(
            LIST_URL,
            data={"name": "Família Pai", "members": []},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    # ------------------------------------------------------------------ #
    # detail / patch / delete                                            #
    # ------------------------------------------------------------------ #
    def test_patch_replaces_members(self):
        group = VisitorGroupModel.objects.create(host_user=self.user_a, name="G")
        group.members.create(name="Old")
        self.authenticate(self.user_a)
        response = self.client.patch(
            detail_url(group.id),
            data={"members": [{"name": "New1"}, {"name": "New2"}]},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        names = [m["name"] for m in response.data["members"]]
        self.assertEqual(sorted(names), ["New1", "New2"])

    def test_delete_group(self):
        group = VisitorGroupModel.objects.create(host_user=self.user_a, name="G")
        self.authenticate(self.user_a)
        response = self.client.delete(detail_url(group.id))
        self.assertEqual(response.status_code, 204)
        self.assertFalse(VisitorGroupModel.objects.filter(id=group.id).exists())

    def test_other_user_cannot_access(self):
        group = VisitorGroupModel.objects.create(host_user=self.user_a, name="Mine")
        self.authenticate(self.user_b)
        self.assertEqual(self.client.get(detail_url(group.id)).status_code, 404)

    # ------------------------------------------------------------------ #
    # schedule (one visit per group member)                              #
    # ------------------------------------------------------------------ #
    def test_schedule_creates_one_visit_per_member(self):
        group = VisitorGroupModel.objects.create(host_user=self.user_a, name="G")
        group.members.create(name="A", email="a@x.com")
        group.members.create(name="B", email="b@x.com")
        self.authenticate(self.user_a)
        response = self.client.post(
            schedule_url(group.id),
            data={"scheduled_date": self._future(), "all_day": False},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 2)
        names = sorted(row["visitor_name"] for row in response.data)
        self.assertEqual(names, ["A", "B"])
        self.assertTrue(all(row["is_group"] for row in response.data))

        visits = VisitorAccessModel.objects.filter(visitor_group=group)
        self.assertEqual(visits.count(), 2)
        self.assertEqual(
            sorted(visits.values_list("visitor_name", flat=True)), ["A", "B"]
        )
        self.assertEqual(visits.first().host_user_id, self.user_a.id)

    def test_schedule_all_day_visit(self):
        group = VisitorGroupModel.objects.create(host_user=self.user_a, name="G")
        group.members.create(name="A", email="a@x.com")
        self.authenticate(self.user_a)
        response = self.client.post(
            schedule_url(group.id),
            data={"scheduled_date": self._future(), "all_day": True},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        visit = VisitorAccessModel.objects.filter(visitor_group=group).first()
        self.assertTrue(visit.all_day)
        local_in = timezone.localtime(visit.checkin_date_time)
        local_out = timezone.localtime(visit.checkout_date_time)
        self.assertEqual(local_in.hour, 0)
        self.assertEqual(local_out.hour, 23)

    def test_empty_group_cannot_be_scheduled(self):
        group = VisitorGroupModel.objects.create(host_user=self.user_a, name="G")
        self.authenticate(self.user_a)
        response = self.client.post(
            schedule_url(group.id),
            data={"scheduled_date": self._future()},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    # ------------------------------------------------------------------ #
    # listing separation: solo vs group visits                           #
    # ------------------------------------------------------------------ #
    def test_solo_listing_excludes_group_visits(self):
        VisitorAccessModel.objects.create(
            host_user=self.user_a,
            visitor_name="Solo",
            scheduled_date=timezone.now() + timedelta(days=1),
            checkin_date_time=timezone.now() + timedelta(days=1),
            checkout_date_time=timezone.now() + timedelta(days=1, hours=3),
            status=VisitorAccessModel.Status.SCHEDULED,
        )
        group = VisitorGroupModel.objects.create(host_user=self.user_a, name="G")
        group.members.create(name="A", email="a@x.com")
        VisitorAccessModel.objects.create(
            host_user=self.user_a,
            visitor_group=group,
            visitor_name="A",
            email="a@x.com",
            scheduled_date=timezone.now() + timedelta(days=1),
            checkin_date_time=timezone.now() + timedelta(days=1),
            checkout_date_time=timezone.now() + timedelta(days=1, hours=3),
            status=VisitorAccessModel.Status.SCHEDULED,
        )

        self.authenticate(self.user_a)
        solo = self.client.get(SOLO_VISITS_LIST_URL)
        self.assertEqual(solo.status_code, 200)
        names = [r["visitor_name"] for r in solo.data["results"]]
        self.assertEqual(names, ["Solo"])

        groups = self.client.get(GROUP_VISITS_LIST_URL)
        self.assertEqual(groups.status_code, 200)
        names = [r["visitor_name"] for r in groups.data["results"]]
        self.assertEqual(names, ["A"])
        self.assertTrue(groups.data["results"][0]["is_group"])

    def test_group_visits_list_other_user_isolated(self):
        group_a = VisitorGroupModel.objects.create(host_user=self.user_a, name="GA")
        group_a.members.create(name="A")
        VisitorAccessModel.objects.create(
            host_user=self.user_a,
            visitor_group=group_a,
            visitor_name="GA",
            scheduled_date=timezone.now() + timedelta(days=1),
            checkin_date_time=timezone.now() + timedelta(days=1),
            checkout_date_time=timezone.now() + timedelta(days=1, hours=3),
            status=VisitorAccessModel.Status.SCHEDULED,
        )
        self.authenticate(self.user_b)
        response = self.client.get(GROUP_VISITS_LIST_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"], [])

    def test_group_visit_cancellation_uses_shared_detail_endpoint(self):
        group = VisitorGroupModel.objects.create(host_user=self.user_a, name="G")
        group.members.create(name="A", email="a@x.com")
        visit = VisitorAccessModel.objects.create(
            host_user=self.user_a,
            visitor_group=group,
            visitor_name="A",
            email="a@x.com",
            scheduled_date=timezone.now() + timedelta(days=2),
            checkin_date_time=timezone.now() + timedelta(days=2),
            checkout_date_time=timezone.now() + timedelta(days=2, hours=3),
            status=VisitorAccessModel.Status.SCHEDULED,
        )
        self.authenticate(self.user_a)
        response = self.client.delete(
            reverse("visitor_access:detail", kwargs={"pk": visit.id})
        )
        self.assertEqual(response.status_code, 204)
        visit.refresh_from_db()
        self.assertEqual(visit.status, VisitorAccessModel.Status.CANCELLED)
