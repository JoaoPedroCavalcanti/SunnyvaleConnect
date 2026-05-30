"""Read / update / delete & permission tests for the users API."""

from django.urls import reverse

from tests_base.base_tests_user import BaseTestsUsers


LIST_URL = reverse("users:users-api-list")


def detail_url(user_id: int) -> str:
    return reverse("users:users-api-detail", kwargs={"pk": user_id})


ME_URL = reverse("users:users-api-me")


class UsersListPermissionTests(BaseTestsUsers):
    def test_anonymous_cannot_list(self):
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 401)

    def test_regular_user_sees_only_self(self):
        self.authenticate(self.user_a)
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        results = response.data["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], self.user_a.id)

    def test_admin_sees_all_users(self):
        self.authenticate(self.admin)
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        # admin + user_a + user_b
        self.assertGreaterEqual(response.data["count"], 3)


class UsersCreatePermissionTests(BaseTestsUsers):
    def test_anonymous_can_create(self):
        payload = self.create_random_user_from_faker()
        response = self.client.post(LIST_URL, data=payload)
        self.assertEqual(response.status_code, 201)

    def test_regular_user_cannot_create(self):
        self.authenticate(self.user_a)
        payload = self.create_random_user_from_faker()
        response = self.client.post(LIST_URL, data=payload)
        self.assertEqual(response.status_code, 403)

    def test_admin_can_create(self):
        self.authenticate(self.admin)
        payload = self.create_random_user_from_faker()
        response = self.client.post(LIST_URL, data=payload)
        self.assertEqual(response.status_code, 201)


class UsersDetailPermissionTests(BaseTestsUsers):
    def test_user_cannot_read_other_users_detail(self):
        self.authenticate(self.user_a)
        response = self.client.get(detail_url(self.user_b.id))
        # user_a's queryset only includes itself → 404
        self.assertEqual(response.status_code, 404)

    def test_admin_can_read_other_users_detail(self):
        self.authenticate(self.admin)
        response = self.client.get(detail_url(self.user_a.id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.user_a.id)


class MeEndpointTests(BaseTestsUsers):
    def test_anonymous_blocked(self):
        response = self.client.get(ME_URL)
        self.assertEqual(response.status_code, 401)

    def test_me_returns_current_user(self):
        self.authenticate(self.user_a)
        response = self.client.get(ME_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.user_a.id)

    def test_me_patch_updates_current_user(self):
        self.authenticate(self.user_a)
        response = self.client.patch(ME_URL, data={"first_name": "Updated"})
        self.assertEqual(response.status_code, 200)
        self.user_a.refresh_from_db()
        self.assertEqual(self.user_a.first_name, "Updated")


class UsersDeleteTests(BaseTestsUsers):
    def test_admin_can_delete_user(self):
        self.authenticate(self.admin)
        response = self.client.delete(detail_url(self.user_a.id))
        self.assertEqual(response.status_code, 204)

    def test_user_cannot_delete_other_user(self):
        self.authenticate(self.user_a)
        response = self.client.delete(detail_url(self.user_b.id))
        # not in queryset → 404
        self.assertEqual(response.status_code, 404)
