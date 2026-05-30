from django.contrib.auth import get_user_model
from faker import Faker
from model_bakery import baker
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import AccessToken

fake = Faker()


class BaseTestsUsers(APITestCase):
    """
    Shared scaffold:
      • self.admin   – staff user (also authenticated client when needed)
      • self.user_a  – regular user
      • self.user_b  – another regular user
      • self.token_user_{a,b} – JWT for the regular users
      • self.client  – DRF APIClient (anonymous by default)
    """

    @classmethod
    def setUpTestData(cls):
        cls.User = get_user_model()
        cls.admin = cls.User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="Abcd123!",
        )
        cls.user_a = baker.make(cls.User)
        cls.user_b = baker.make(cls.User)
        cls.token_user_a = AccessToken.for_user(cls.user_a)
        cls.token_user_b = AccessToken.for_user(cls.user_b)
        cls.token_admin = AccessToken.for_user(cls.admin)

    def authenticate(self, user):
        """Attach JWT credentials for the given user to self.client."""
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}"
        )
        return self.client

    def logout(self):
        self.client.credentials()

    def get_client_for(self, user) -> APIClient:
        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}"
        )
        return client

    def create_random_user_from_faker(self):
        return {
            "username": fake.user_name(),
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": fake.email(),
            "password": "StrongPass1!",
        }
