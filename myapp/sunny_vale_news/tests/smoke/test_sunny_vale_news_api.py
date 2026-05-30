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
            LIST_URL, data={"title": "x", "description": "y", "author": "z"}
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_can_create(self):
        self.authenticate(self.admin)
        response = self.client.post(
            LIST_URL, data={"title": "x", "description": "y", "author": "z"}
        )
        self.assertEqual(response.status_code, 201, response.data)

    def test_detail_not_found(self):
        self.authenticate(self.admin)
        self.assertEqual(self.client.get(detail_url(999999)).status_code, 404)
