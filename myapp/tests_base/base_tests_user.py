from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework_simplejwt.tokens import AccessToken
from model_bakery import baker
from faker import Faker

fake = Faker()


class BaseTestsUsers(TestCase):
    def setUp(self):
        self.User = get_user_model()

        self.admin = self.User.objects.create_superuser(
            username="admin", email="admin@gmail.com", password="Abcd123!"
        )
        self.user_a = baker.make(self.User)
        self.user_b = baker.make(self.User)

        self.token_user_a = AccessToken.for_user(self.user_a)
        self.token_user_b = AccessToken.for_user(self.user_b)

    def create_random_user_from_faker(self):
        user = {
            "username": fake.user_name(),
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": fake.email(),
            "password": fake.password(),
        }
        return user
