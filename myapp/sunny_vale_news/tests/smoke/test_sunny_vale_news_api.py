"""Smoke tests for the SunnyVale News API."""

import pytest
from django.urls import reverse
from model_bakery import baker

from sunny_vale_news.models import SunnyValeNewsModel
from tests_base.base_tests_user import BaseTestsUsers


pytestmark = pytest.mark.api


LIST_URL = reverse("sunny_vale_news:list-create")


def detail_url(pk):
    return reverse("sunny_vale_news:detail", kwargs={"pk": pk})


class SunnyValeNewsAPISmoke(BaseTestsUsers):
    def test_anonymous_blocked(self):
        self.assertEqual(self.client.get(LIST_URL).status_code, 401)

    def test_user_can_read(self):
        baker.make(SunnyValeNewsModel)
        self.authenticate(self.user_a)
        self.assertEqual(self.client.get(LIST_URL).status_code, 200)

    def test_user_cannot_create(self):
        self.authenticate(self.user_a)
        response = self.client.post(
            LIST_URL, data={"title": "x", "description": "y"}
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_can_create(self):
        self.authenticate(self.admin)
        response = self.client.post(
            LIST_URL,
            data={
                "title": "x",
                "description": "y",
                "kind": "EVENT",
                "priority_level": "high",
            },
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["kind"], "EVENT")
        self.assertEqual(response.data["priority_level"], "high")

    def test_create_stamps_authorship_from_authenticated_user(self):
        self.authenticate(self.admin)
        response = self.client.post(
            LIST_URL, data={"title": "x", "description": "y"}
        )
        self.assertEqual(response.status_code, 201, response.data)
        created_by = response.data["created_by"]
        self.assertEqual(created_by["id"], self.admin.id)
        self.assertEqual(created_by["full_name"], self.admin.full_name)
        self.assertEqual(created_by["role"], "ADMIN")

    def test_create_default_kind_is_notice(self):
        self.authenticate(self.admin)
        response = self.client.post(
            LIST_URL, data={"title": "x", "description": "y"}
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["kind"], "NOTICE")

    def test_kind_filter(self):
        baker.make(SunnyValeNewsModel, kind="NOTICE")
        baker.make(SunnyValeNewsModel, kind="EVENT")
        baker.make(SunnyValeNewsModel, kind="EVENT")
        self.authenticate(self.user_a)
        response = self.client.get(LIST_URL, {"kind": "EVENT"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        for row in response.data["results"]:
            self.assertEqual(row["kind"], "EVENT")

    def test_detail_not_found(self):
        self.authenticate(self.admin)
        self.assertEqual(self.client.get(detail_url(999999)).status_code, 404)

    def test_admin_cannot_overwrite_authorship_via_patch(self):
        self.authenticate(self.admin)
        created = self.client.post(
            LIST_URL, data={"title": "x", "description": "y"}
        ).data
        response = self.client.patch(
            detail_url(created["id"]),
            data={"title": "new title", "author": "hijacker", "author_role": "GHOST"},
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["title"], "new title")
        self.assertEqual(
            response.data["created_by"]["full_name"], self.admin.full_name
        )
        self.assertEqual(response.data["created_by"]["role"], "ADMIN")
