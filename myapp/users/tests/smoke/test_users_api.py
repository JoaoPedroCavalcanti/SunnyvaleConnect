"""Smoke tests for the users API. One happy + one sad case per endpoint."""

import pytest
from django.urls import reverse

from tests_base.base_tests_user import BaseTestsUsers


pytestmark = pytest.mark.api


LIST_URL = reverse("users:users-api-list")
ME_URL = reverse("users:users-api-me")


def detail_url(pk: int) -> str:
    return reverse("users:users-api-detail", kwargs={"pk": pk})


class UsersAPISmoke(BaseTestsUsers):
    def test_anonymous_blocked(self):
        self.assertEqual(self.client.get(LIST_URL).status_code, 401)

    def test_anonymous_can_register(self):
        response = self.client.post(LIST_URL, data=self.create_random_user_from_faker())
        self.assertEqual(response.status_code, 201)

    def test_regular_user_lists_only_self(self):
        self.authenticate(self.user_a)
        results = self.client.get(LIST_URL).data["results"]
        self.assertEqual(len(results), 1)

    def test_admin_lists_all(self):
        self.authenticate(self.admin)
        self.assertGreaterEqual(self.client.get(LIST_URL).data["count"], 3)

    def test_admin_list_excludes_inactive_by_default(self):
        self.user_b.is_active = False
        self.user_b.save(update_fields=["is_active"])
        self.authenticate(self.admin)
        ids = {u["id"] for u in self.client.get(LIST_URL).data["results"]}
        self.assertNotIn(self.user_b.id, ids)
        self.assertIn(self.user_a.id, ids)
        inactive_ids = {
            u["id"]
            for u in self.client.get(LIST_URL, {"is_active": "false"}).data[
                "results"
            ]
        }
        self.assertIn(self.user_b.id, inactive_ids)

    def test_me_returns_current_user(self):
        self.authenticate(self.user_a)
        response = self.client.get(ME_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.user_a.id)

    def test_user_detail_404_for_others(self):
        self.authenticate(self.user_a)
        self.assertEqual(self.client.get(detail_url(self.user_b.id)).status_code, 404)

    def test_weak_password_rejected(self):
        payload = self.create_random_user_from_faker()
        payload["password"] = "a"
        response = self.client.post(LIST_URL, data=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.data)

    def test_duplicate_email_rejected(self):
        payload = self.create_random_user_from_faker()
        payload["email"] = self.user_a.email
        response = self.client.post(LIST_URL, data=payload)
        self.assertEqual(response.status_code, 400)

    def test_duplicate_cpf_rejected(self):
        payload = self.create_random_user_from_faker()
        payload["cpf"] = self.user_a.cpf
        response = self.client.post(LIST_URL, data=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("cpf", response.data)

    def test_invalid_cpf_rejected(self):
        payload = self.create_random_user_from_faker()
        payload["cpf"] = "11111111111"
        response = self.client.post(LIST_URL, data=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("cpf", response.data)

    def test_admin_can_delete_user(self):
        self.authenticate(self.admin)
        self.assertEqual(
            self.client.delete(detail_url(self.user_a.id)).status_code, 204
        )
        self.user_a.refresh_from_db()
        self.assertFalse(self.user_a.is_active)

    def test_resident_cannot_deactivate_self(self):
        self.authenticate(self.user_a)
        response = self.client.delete(detail_url(self.user_a.id))
        self.assertEqual(response.status_code, 403)

    def test_admin_can_edit_user_identifiers(self):
        self.authenticate(self.admin)
        new_cpf = self.create_random_user_from_faker()["cpf"]
        response = self.client.patch(
            detail_url(self.user_a.id),
            data={
                "username": "updated-user",
                "cpf": new_cpf,
                "email": "UPDATED@EXAMPLE.COM",
            },
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["username"], "updated-user")
        self.assertEqual(response.data["cpf"], new_cpf)
        self.assertEqual(response.data["email"], "updated@example.com")

    def test_admin_deactivating_owner_transfers_ownership(self):
        from units.models import Unit, UnitMembership

        unit = Unit.objects.create(
            kind=Unit.Kind.APARTMENT_BLOCK,
            apartment="808",
            block="T",
            condominium=self.condominium,
        )
        owner = UnitMembership.objects.create(
            unit=unit,
            user=self.user_a,
            role=UnitMembership.Role.OWNER,
            status=UnitMembership.Status.ACTIVE,
        )
        replacement = UnitMembership.objects.create(
            unit=unit,
            user=self.user_b,
            role=UnitMembership.Role.RESIDENT,
            status=UnitMembership.Status.ACTIVE,
        )
        self.authenticate(self.admin)

        response = self.client.delete(detail_url(self.user_a.id))

        self.assertEqual(response.status_code, 204)
        owner.refresh_from_db()
        replacement.refresh_from_db()
        self.assertEqual(owner.status, UnitMembership.Status.LEFT)
        self.assertEqual(replacement.role, UnitMembership.Role.OWNER)

    def test_anonymous_signup_defaults_to_resident(self):
        payload = self.create_random_user_from_faker()
        response = self.client.post(LIST_URL, data=payload)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["role"], "RESIDENT")

    def test_anonymous_cannot_self_assign_admin(self):
        payload = self.create_random_user_from_faker()
        payload["role"] = "ADMIN"
        response = self.client.post(LIST_URL, data=payload)
        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_employee(self):
        self.authenticate(self.admin)
        payload = self.create_random_user_from_faker()
        payload["role"] = "EMPLOYEE"
        payload["employee_types"] = ["CLEANING"]
        payload.pop("apartment", None)
        payload.pop("block", None)
        response = self.client.post(LIST_URL, data=payload)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["role"], "EMPLOYEE")

    def test_admin_can_create_admin(self):
        self.authenticate(self.admin)
        payload = self.create_random_user_from_faker()
        payload["role"] = "ADMIN"
        response = self.client.post(LIST_URL, data=payload)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["role"], "ADMIN")

    def test_admin_cannot_create_resident_without_unit(self):
        self.authenticate(self.admin)
        payload = self.create_random_user_from_faker()
        payload["role"] = "RESIDENT"

        response = self.client.post(LIST_URL, data=payload, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("unit_request", response.data)

    def test_admin_creates_resident_joining_vacant_unit_is_active(self):
        from units.models import Unit, UnitMembership

        vacant = Unit.objects.create(
            kind=Unit.Kind.APARTMENT_BLOCK,
            apartment="901",
            block="X",
            status=Unit.Status.ACTIVE,
            condominium=self.condominium,
        )

        self.authenticate(self.admin)
        payload = self.create_random_user_from_faker()
        payload["unit_request"] = {"unit_id": vacant.id}
        response = self.client.post(LIST_URL, data=payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)

        user = self.User.objects.get(pk=response.data["id"])
        self.assertTrue(user.is_active)

        membership = vacant.memberships.get(user=user)
        self.assertEqual(membership.status, UnitMembership.Status.ACTIVE)
        self.assertEqual(membership.role, UnitMembership.Role.OWNER)

    def test_admin_creates_resident_joining_existing_unit_is_active(self):
        from units.models import Unit, UnitMembership

        unit = Unit.objects.create(
            kind=Unit.Kind.APARTMENT_BLOCK,
            apartment="1201",
            block="F",
            status=Unit.Status.ACTIVE,
            condominium=self.condominium,
        )
        UnitMembership.objects.create(
            unit=unit,
            user=self.user_a,
            role=UnitMembership.Role.OWNER,
            status=UnitMembership.Status.ACTIVE,
        )

        self.authenticate(self.admin)
        payload = self.create_random_user_from_faker()
        payload["unit_request"] = {"unit_id": unit.id}
        response = self.client.post(LIST_URL, data=payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)

        user = self.User.objects.get(pk=response.data["id"])
        self.assertTrue(user.is_active)
        membership = unit.memberships.get(user=user)
        self.assertEqual(membership.status, UnitMembership.Status.ACTIVE)
        self.assertEqual(membership.role, UnitMembership.Role.RESIDENT)

    def test_resident_cannot_create_employee(self):
        self.authenticate(self.user_a)
        payload = self.create_random_user_from_faker()
        payload["role"] = "EMPLOYEE"
        response = self.client.post(LIST_URL, data=payload)
        self.assertEqual(response.status_code, 403)

    def test_admin_cannot_demote_self_via_patch(self):
        self.authenticate(self.admin)
        response = self.client.patch(
            detail_url(self.admin.id),
            data={"role": "RESIDENT"},
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_cannot_delete_self(self):
        self.authenticate(self.admin)
        response = self.client.delete(detail_url(self.admin.id))
        self.assertEqual(response.status_code, 403)

    def test_admin_cannot_deactivate_self_via_patch(self):
        self.authenticate(self.admin)
        response = self.client.patch(
            detail_url(self.admin.id), data={"is_active": False}
        )
        self.assertEqual(response.status_code, 403)

    def test_resident_cannot_change_own_role(self):
        self.authenticate(self.user_a)
        response = self.client.patch(ME_URL, data={"role": "ADMIN"})
        self.assertEqual(response.status_code, 403)

    def test_admin_can_promote_user_to_employee(self):
        self.authenticate(self.admin)
        response = self.client.patch(
            detail_url(self.user_a.id),
            data={"role": "EMPLOYEE", "employee_types": ["DOORMAN"]},
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["role"], "EMPLOYEE")

    def test_role_filter_lists_only_matching(self):
        self.authenticate(self.admin)
        emp_payload = self.create_random_user_from_faker()
        emp_payload["role"] = "EMPLOYEE"
        emp_payload["employee_types"] = ["CLEANING"]
        emp_payload.pop("apartment", None)
        emp_payload.pop("block", None)
        self.client.post(LIST_URL, data=emp_payload)

        response = self.client.get(LIST_URL, {"role": "EMPLOYEE"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["role"], "EMPLOYEE")

    def test_admin_list_without_role_includes_employee(self):
        self.authenticate(self.admin)
        emp_payload = self.create_random_user_from_faker()
        emp_payload["role"] = "EMPLOYEE"
        emp_payload["employee_types"] = ["DOORMAN"]
        emp_payload.pop("apartment", None)
        emp_payload.pop("block", None)
        create_response = self.client.post(LIST_URL, data=emp_payload)
        self.assertEqual(create_response.status_code, 201, create_response.data)

        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        roles = {item["role"] for item in response.data["results"]}
        self.assertIn("EMPLOYEE", roles)
        employee_ids = {
            item["id"]
            for item in response.data["results"]
            if item["role"] == "EMPLOYEE"
        }
        self.assertIn(create_response.data["id"], employee_ids)


LOGIN_URL = "/api/token/"


class LoginAPISmoke(BaseTestsUsers):
    def test_active_user_gets_tokens(self):
        response = self.client.post(
            LOGIN_URL,
            data=self.login_payload(self.user_a),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_access_token_carries_role_claim(self):
        from rest_framework_simplejwt.tokens import AccessToken

        response = self.client.post(
            LOGIN_URL,
            data=self.login_payload(self.admin, password="Abcd123!"),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        token = AccessToken(response.data["access"])
        self.assertEqual(token["role"], "ADMIN")

    def test_invalid_credentials_returns_401(self):
        payload = self.login_payload(self.user_a)
        payload["password"] = "wrong"
        response = self.client.post(
            LOGIN_URL,
            data=payload,
            format="json",
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["code"], "invalid_credentials")

    def test_pending_user_returns_403_with_unit_info(self):
        from units.models import Unit, UnitMembership

        self.user_a.is_active = False
        self.user_a.save()
        unit = Unit.objects.create(
            kind=Unit.Kind.APARTMENT_BLOCK,
            apartment="701",
            block="C",
            status=Unit.Status.ACTIVE,
            condominium=self.condominium,
        )
        UnitMembership.objects.create(
            unit=unit,
            user=self.user_a,
            role=UnitMembership.Role.OWNER,
            status=UnitMembership.Status.PENDING_ADMIN,
        )

        response = self.client.post(
            LOGIN_URL,
            data=self.login_payload(self.user_a),
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["code"], "pending_unit_approval")
        self.assertEqual(response.data["unit"]["display_name"], "Apt 701 / Block C")

    def test_signup_with_unit_holds_pending_until_otp(self):
        from django.core import mail

        from shared.container import container
        from shared.test_doubles.fakes import FakeCodeGenerator
        from units.models import Unit, UnitMembership

        codes = FakeCodeGenerator("998877")
        container.override("code_generator", codes)

        vacant = Unit.objects.create(
            kind=Unit.Kind.APARTMENT_BLOCK,
            apartment="880",
            block="Z",
            status=Unit.Status.ACTIVE,
            condominium=self.condominium,
        )
        payload = self.create_random_user_from_faker()
        payload["unit_request"] = {"unit_id": vacant.id}
        signup = self.client.post(LIST_URL, data=payload, format="json")
        self.assertEqual(signup.status_code, 202, signup.data)
        self.assertEqual(signup.data["code"], "pending_email_verification")
        self.assertFalse(
            self.User.objects.filter(email=payload["email"]).exists()
        )
        self.assertEqual(vacant.memberships.count(), 0)
        self.assertTrue(
            any("Verify your email" in m.subject for m in mail.outbox)
        )

        response = self.client.post(
            reverse("users:verify-email"),
            data={"email": payload["email"], "code": codes.six_digits()},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)

        user = self.User.objects.get(email=payload["email"])
        self.assertFalse(user.is_active)
        membership = vacant.memberships.get(user=user)
        self.assertEqual(membership.status, UnitMembership.Status.PENDING_ADMIN)

    def test_verify_email_rejects_wrong_code_without_creating_user(self):
        from shared.container import container
        from shared.test_doubles.fakes import FakeCodeGenerator
        from units.models import Unit

        codes = FakeCodeGenerator("112233")
        container.override("code_generator", codes)

        vacant = Unit.objects.create(
            kind=Unit.Kind.APARTMENT_BLOCK,
            apartment="881",
            block="Z",
            status=Unit.Status.ACTIVE,
            condominium=self.condominium,
        )
        payload = self.create_random_user_from_faker()
        payload["unit_request"] = {"unit_id": vacant.id}
        signup = self.client.post(LIST_URL, data=payload, format="json")
        self.assertEqual(signup.status_code, 202, signup.data)

        response = self.client.post(
            reverse("users:verify-email"),
            data={"email": payload["email"], "code": "000000"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(
            self.User.objects.filter(email=payload["email"]).exists()
        )
        self.assertEqual(vacant.memberships.count(), 0)
