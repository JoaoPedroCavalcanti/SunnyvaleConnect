"""Unit tests for Django admin user forms."""

import pytest

from condominiums.models import Condominium
from shared.tenant import build_tenant_username
from users.forms import SunnyvaleUserAddForm, SunnyvaleUserChangeForm
from users.models import User, UserRole

pytestmark = pytest.mark.unit


@pytest.fixture
def condominium(db):
    return Condominium.objects.create(
        name="Chacon Residence",
        slug="chacon-residence",
        code="I93TD8Z9",
        is_active=True,
    )


def _add_form_data(condominium, **overrides):
    data = {
        "condominium": str(condominium.pk),
        "username": "admin",
        "password1": "Abcd1234!",
        "password2": "Abcd1234!",
        "email": "admin@condo.com",
        "full_name": "Condo Admin",
        "birth_date": "1990-01-01",
        "cpf": "52998224725",
        "phone": "11999999999",
        "role": UserRole.ADMIN,
        "employee_types": "[]",
        "is_active": "on",
    }
    data.update(overrides)
    return data


@pytest.mark.django_db
def test_add_form_requires_condominium(condominium):
    data = _add_form_data(condominium)
    data.pop("condominium")
    form = SunnyvaleUserAddForm(data=data)
    assert not form.is_valid()
    assert "condominium" in form.errors


@pytest.mark.django_db
def test_add_form_prefixes_username_and_sets_is_staff(condominium):
    form = SunnyvaleUserAddForm(data=_add_form_data(condominium))
    assert form.is_valid(), form.errors
    assert form.cleaned_data["username"] == build_tenant_username(
        condominium.code, "admin"
    )
    assert form.cleaned_data["is_staff"] is True


@pytest.mark.django_db
def test_change_form_keeps_superuser_without_condominium(condominium):
    user = User.objects.create_superuser(
        username="platform",
        email="super@platform.com",
        password="Abcd1234!",
        full_name="Platform Super",
        birth_date="1990-01-01",
        cpf="39053344705",
        phone="11988887777",
    )
    form = SunnyvaleUserChangeForm(
        data={
            "username": user.username,
            "password": user.password,
            "condominium": "",
            "full_name": user.full_name,
            "birth_date": "1990-01-01",
            "cpf": user.cpf,
            "phone": user.phone,
            "email": user.email,
            "apartment": "",
            "block": "",
            "role": UserRole.RESIDENT,
            "employee_types": "[]",
            "is_active": "on",
            "is_superuser": "on",
            "is_staff": "on",
            "groups": [],
            "user_permissions": [],
            "date_joined": user.date_joined.strftime("%Y-%m-%d %H:%M:%S"),
        },
        instance=user,
    )
    assert form.is_valid(), form.errors
    assert form.cleaned_data["condominium"] is None


@pytest.mark.django_db
def test_change_form_rejects_superuser_with_condominium(condominium):
    user = User.objects.create_superuser(
        username="platform",
        email="super@platform.com",
        password="Abcd1234!",
        full_name="Platform Super",
        birth_date="1990-01-01",
        cpf="39053344705",
        phone="11988887777",
    )
    form = SunnyvaleUserChangeForm(
        data={
            "username": user.username,
            "password": user.password,
            "condominium": str(condominium.pk),
            "full_name": user.full_name,
            "birth_date": "1990-01-01",
            "cpf": user.cpf,
            "phone": user.phone,
            "email": user.email,
            "apartment": "",
            "block": "",
            "role": UserRole.RESIDENT,
            "employee_types": "[]",
            "is_active": "on",
            "is_superuser": "on",
            "is_staff": "on",
            "groups": [],
            "user_permissions": [],
            "date_joined": user.date_joined.strftime("%Y-%m-%d %H:%M:%S"),
        },
        instance=user,
    )
    assert not form.is_valid()
    assert "condominium" in form.errors
