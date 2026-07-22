"""Tests for CondominiumAdminForm module persistence."""

import pytest
from django.contrib.admin.sites import AdminSite

from condominiums.admin import CondominiumAdmin, CondominiumAdminForm
from condominiums.models import Condominium
from condominiums.modules import ALL_MODULE_KEYS


pytestmark = pytest.mark.django_db


def test_admin_form_saves_subset_even_if_enable_all_is_checked():
    condo = Condominium.objects.create(
        name="Chacon Test",
        slug="chacon-test-modules",
        code="TSTMOD01",
        enabled_modules=list(ALL_MODULE_KEYS),
    )
    form = CondominiumAdminForm(
        data={
            "name": condo.name,
            "slug": condo.slug,
            "code": condo.code,
            "is_active": "on",
            "primary_color": condo.primary_color,
            "secondary_color": condo.secondary_color,
            "accent_color": condo.accent_color,
            "welcome_message": "",
            # Bug reproduction: "all" left checked while only two modules selected.
            "enable_all_modules": "on",
            "enabled_modules": ["visitor_access", "reservations"],
        },
        instance=condo,
    )
    assert form.is_valid(), form.errors
    saved = form.save()
    assert saved.enabled_modules == ["visitor_access", "reservations"]


def test_admin_form_initial_reflects_saved_subset():
    condo = Condominium.objects.create(
        name="Partial",
        slug="partial-modules",
        code="PARTIAL1",
        enabled_modules=["sunny_vale_news"],
    )
    form = CondominiumAdminForm(instance=condo)
    assert form.fields["enabled_modules"].initial == ["sunny_vale_news"]
    assert form.fields["enable_all_modules"].initial is False


def test_admin_registered_with_modules_fieldset():
    site = AdminSite()
    model_admin = CondominiumAdmin(Condominium, site)
    titles = [title for title, _ in model_admin.fieldsets]
    assert "Módulos" in titles
