from django.urls import reverse, NoReverseMatch
from model_bakery import baker

from sunny_vale_news.models import SunnyValeNewsModel
from tests_base.base_tests_user import BaseTestsUsers


def _list_url() -> str:
    try:
        return reverse("sunny_vale_new-list")
    except NoReverseMatch:
        return "/sunny_vale_news/"


def _detail_url(pk: int) -> str:
    try:
        return reverse("sunny_vale_new-detail", kwargs={"pk": pk})
    except NoReverseMatch:
        return f"/sunny_vale_news/{pk}/"


LIST_URL = _list_url()


class NewsPermissionTests(BaseTestsUsers):
    def test_anonymous_blocked(self):
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 401)

    def test_regular_user_can_read(self):
        baker.make(SunnyValeNewsModel, _quantity=2)
        self.authenticate(self.user_a)
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)

    def test_regular_user_cannot_create(self):
        self.authenticate(self.user_a)
        response = self.client.post(
            LIST_URL,
            data={"title": "T", "description": "D", "author": "A"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)


class NewsAdminCRUDTests(BaseTestsUsers):
    def test_admin_create(self):
        self.authenticate(self.admin)
        response = self.client.post(
            LIST_URL,
            data={
                "title": "Pool renovation",
                "description": "Closed for the weekend",
                "author": "Manager",
                "priority_level": "high",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)

    def test_admin_update(self):
        obj = baker.make(SunnyValeNewsModel, title="Old")
        self.authenticate(self.admin)
        response = self.client.patch(
            _detail_url(obj.id), data={"title": "New"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        obj.refresh_from_db()
        self.assertEqual(obj.title, "New")

    def test_admin_delete(self):
        obj = baker.make(SunnyValeNewsModel)
        self.authenticate(self.admin)
        response = self.client.delete(_detail_url(obj.id))
        self.assertEqual(response.status_code, 204)
        self.assertFalse(SunnyValeNewsModel.objects.filter(pk=obj.id).exists())


class NewsValidationTests(BaseTestsUsers):
    def test_missing_required_fields_returns_400(self):
        self.authenticate(self.admin)
        response = self.client.post(LIST_URL, data={}, format="json")
        self.assertEqual(response.status_code, 400)
        for field in ["title", "description", "author"]:
            self.assertIn(field, response.data)
