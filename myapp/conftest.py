"""
Global pytest fixtures.

`pytest-django` already wires Django up via the `DJANGO_SETTINGS_MODULE`
declared in pyproject.toml — no need for an explicit `django.setup()`.
"""

import pytest
from django.contrib.auth import get_user_model
from faker import Faker
from model_bakery import baker
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

fake = Faker()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user_factory(db):
    """Bake regular users on demand."""

    def _make(**overrides):
        return baker.make(get_user_model(), **overrides)

    return _make


@pytest.fixture
def admin_user(db):
    return get_user_model().objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="Abcd123!",
    )


@pytest.fixture
def regular_user(user_factory):
    return user_factory()


def _authenticate(client: APIClient, user) -> APIClient:
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")
    return client


@pytest.fixture
def admin_client(api_client, admin_user):
    return _authenticate(api_client, admin_user)


@pytest.fixture
def auth_client(api_client, regular_user):
    return _authenticate(api_client, regular_user)


@pytest.fixture
def faker_instance():
    return fake


@pytest.fixture
def fake_user_payload():
    """Valid payload for the `users-api` create endpoint."""
    return {
        "username": fake.user_name(),
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "email": fake.email(),
        "password": "StrongPass1!",
    }
