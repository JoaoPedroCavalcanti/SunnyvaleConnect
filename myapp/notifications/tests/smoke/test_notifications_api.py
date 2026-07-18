"""Smoke tests for the notifications API."""

import pytest
from django.urls import reverse
from django.utils import timezone

from notifications.models import NotificationModel
from tests_base.base_tests_user import BaseTestsUsers


pytestmark = pytest.mark.api


LIST_URL = reverse("notifications:list")
UNREAD_COUNT_URL = reverse("notifications:unread-count")
MARK_ALL_READ_URL = reverse("notifications:mark-all-read")


def mark_read_url(pk):
    return reverse("notifications:mark-read", kwargs={"pk": pk})


class NotificationAPISmoke(BaseTestsUsers):
    def _make(self, user, *, title="Hello", read=False, **kwargs):
        return NotificationModel.objects.create(
            recipient=user,
            condominium=user.condominium,
            type=kwargs.pop("type", NotificationModel.Type.GENERIC),
            title=title,
            body=kwargs.pop("body", ""),
            data=kwargs.pop("data", {}),
            read_at=timezone.now() if read else None,
        )

    def test_anonymous_blocked(self):
        self.assertEqual(self.client.get(LIST_URL).status_code, 401)

    def test_list_only_own_notifications(self):
        mine = self._make(self.user_a, title="Mine")
        self._make(self.user_b, title="Theirs")
        self.authenticate(self.user_a)

        response = self.client.get(LIST_URL)

        self.assertEqual(response.status_code, 200)
        ids = {row["id"] for row in response.data["results"]}
        self.assertEqual(ids, {mine.id})

    def test_unread_filter_and_count(self):
        unread = self._make(self.user_a, title="Unread")
        self._make(self.user_a, title="Read", read=True)
        self.authenticate(self.user_a)

        listing = self.client.get(LIST_URL + "?unread=true")
        count = self.client.get(UNREAD_COUNT_URL)

        self.assertEqual(listing.status_code, 200)
        self.assertEqual(
            {row["id"] for row in listing.data["results"]}, {unread.id}
        )
        self.assertEqual(count.status_code, 200)
        self.assertEqual(count.data["count"], 1)

    def test_mark_read(self):
        notif = self._make(self.user_a, title="To read")
        self.authenticate(self.user_a)

        response = self.client.patch(mark_read_url(notif.id))

        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["is_read"])
        notif.refresh_from_db()
        self.assertIsNotNone(notif.read_at)

    def test_mark_all_read(self):
        self._make(self.user_a, title="A")
        self._make(self.user_a, title="B")
        self.authenticate(self.user_a)

        response = self.client.post(MARK_ALL_READ_URL)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["updated"], 2)
        self.assertEqual(
            NotificationModel.objects.filter(
                recipient=self.user_a, read_at__isnull=True
            ).count(),
            0,
        )

    def test_cannot_mark_other_users_notification(self):
        notif = self._make(self.user_a, title="Mine")
        self.authenticate(self.user_b)

        response = self.client.patch(mark_read_url(notif.id))

        self.assertEqual(response.status_code, 404)
