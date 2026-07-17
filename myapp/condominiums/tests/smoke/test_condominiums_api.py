"""Smoke tests for platform condominium listing."""

import pytest
from django.urls import reverse

from condominiums.models import Condominium
from tests_base.base_tests_user import BaseTestsUsers


pytestmark = pytest.mark.api


class CondominiumListSmoke(BaseTestsUsers):
    def test_platform_list_is_paginated(self):
        self.admin.is_superuser = True
        self.admin.save(update_fields=["is_superuser"])
        Condominium.objects.bulk_create(
            [
                Condominium(
                    name=f"Condominium {index}",
                    slug=f"condominium-{index}",
                    code=f"C{index:07d}",
                )
                for index in range(11)
            ]
        )
        self.authenticate(self.admin)

        response = self.client.get(reverse("condominiums:list-create"))

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 12)
        self.assertEqual(len(response.data["results"]), 10)
        self.assertIsNotNone(response.data["next"])
