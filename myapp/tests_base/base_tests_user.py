from datetime import date

from django.contrib.auth import get_user_model
from faker import Faker
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import AccessToken

fake = Faker("pt_BR")


def _gen_cpf() -> str:
    """Generate a syntactically valid CPF (digits-only)."""
    import random

    base = [random.randint(0, 9) for _ in range(9)]
    for i in (9, 10):
        total = sum(base[j] * ((i + 1) - j) for j in range(i))
        check = (total * 10) % 11
        base.append(0 if check == 10 else check)
    return "".join(str(d) for d in base)


def _make_user(model, **overrides):
    defaults = {
        "username": fake.unique.user_name(),
        "email": fake.unique.email(),
        "password": "Abcd123!",
        "full_name": fake.name(),
        "birth_date": date(1990, 1, 1),
        "cpf": _gen_cpf(),
        "phone": "11987654321",
        "apartment": "101",
        "block": "A",
    }
    defaults.update(overrides)
    password = defaults.pop("password")
    return model.objects.create_user(password=password, **defaults)


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
            full_name="Admin User",
            birth_date=date(1980, 1, 1),
            cpf=_gen_cpf(),
            phone="11999999999",
            apartment="0",
        )
        cls.user_a = _make_user(cls.User)
        cls.user_b = _make_user(cls.User)
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
            "username": fake.unique.user_name(),
            "email": fake.unique.email(),
            "password": "StrongPass1!",
            "full_name": fake.name(),
            "birth_date": "1995-05-20",
            "cpf": _gen_cpf(),
            "phone": "11987654321",
            "apartment": "202",
            "block": "B",
        }
