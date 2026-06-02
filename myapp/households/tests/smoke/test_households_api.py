"""Smoke tests for the households API: signup flow, approvals, dependents."""

from datetime import date

import pytest
from django.urls import reverse

from households.models import Household, HouseholdMembership
from tests_base.base_tests_user import BaseTestsUsers, _gen_cpf, fake


pytestmark = pytest.mark.api


SIGNUP_URL = reverse("users:users-api-list")
SEARCH_URL = reverse("households:search")
LIST_URL = reverse("households:list")
PENDING_URL = reverse("households:pending-approvals")


def _approve_url(pk):
    return reverse("households:approve", kwargs={"pk": pk})


def _reject_url(pk):
    return reverse("households:reject", kwargs={"pk": pk})


def _detail_url(pk):
    return reverse("households:detail", kwargs={"pk": pk})


def _memberships_list_url(pk):
    return reverse("households:memberships-list", kwargs={"pk": pk})


def _membership_approve_url(pk, mid):
    return reverse(
        "households:membership-approve", kwargs={"pk": pk, "mid": mid}
    )


def _membership_reject_url(pk, mid):
    return reverse(
        "households:membership-reject", kwargs={"pk": pk, "mid": mid}
    )


def _membership_promote_url(pk, mid):
    return reverse(
        "households:membership-promote", kwargs={"pk": pk, "mid": mid}
    )


def _leave_url(pk):
    return reverse("households:leave", kwargs={"pk": pk})


def _transfer_url(pk):
    return reverse("households:transfer", kwargs={"pk": pk})


def _dependents_url(pk):
    return reverse("households:dependents-list-create", kwargs={"pk": pk})


def _signup_payload(**overrides):
    payload = {
        "username": fake.unique.user_name(),
        "email": fake.unique.email(),
        "password": "StrongPass1!",
        "full_name": fake.name(),
        "birth_date": "1990-01-01",
        "cpf": _gen_cpf(),
        "phone": "11987654321",
    }
    payload.update(overrides)
    return payload


class SignupFlowSmoke(BaseTestsUsers):
    def test_signup_with_new_household_returns_pending_user(self):
        payload = _signup_payload()
        payload["household_request"] = {"apartment": "302", "block": "A"}
        response = self.client.post(SIGNUP_URL, data=payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)

        created = self.User.objects.get(pk=response.data["id"])
        self.assertFalse(created.is_active)

        household = Household.objects.get(apartment="302", block="A")
        self.assertEqual(household.status, Household.Status.PENDING_ADMIN)

        membership = household.memberships.get(user=created)
        self.assertEqual(membership.role, HouseholdMembership.Role.HOLDER)
        self.assertEqual(membership.status, HouseholdMembership.Status.PENDING_ADMIN)

    def test_signup_join_existing_household(self):
        household = Household.objects.create(
            apartment="555", block="B", status=Household.Status.ACTIVE
        )
        payload = _signup_payload()
        payload["household_request"] = {"household_id": household.id}
        response = self.client.post(SIGNUP_URL, data=payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)

        created = self.User.objects.get(pk=response.data["id"])
        membership = household.memberships.get(user=created)
        self.assertEqual(membership.status, HouseholdMembership.Status.PENDING_HOLDER)
        self.assertEqual(membership.role, HouseholdMembership.Role.RESIDENT)

    def test_signup_without_household_request_creates_active_user(self):
        response = self.client.post(SIGNUP_URL, data=_signup_payload(), format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(self.User.objects.get(pk=response.data["id"]).is_active)

    def test_signup_copies_apartment_block_from_new_household(self):
        payload = _signup_payload()
        payload["household_request"] = {"apartment": "402", "block": "C"}
        response = self.client.post(SIGNUP_URL, data=payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        user = self.User.objects.get(pk=response.data["id"])
        self.assertEqual(user.apartment, "402")
        self.assertEqual(user.block, "C")

    def test_signup_copies_apartment_block_from_existing_household(self):
        household = Household.objects.create(
            apartment="888", block="D", status=Household.Status.ACTIVE
        )
        payload = _signup_payload()
        payload["household_request"] = {"household_id": household.id}
        response = self.client.post(SIGNUP_URL, data=payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        user = self.User.objects.get(pk=response.data["id"])
        self.assertEqual(user.apartment, "888")
        self.assertEqual(user.block, "D")


class HouseholdSearchSmoke(BaseTestsUsers):
    def test_public_search_returns_active_only(self):
        Household.objects.create(
            apartment="101", block="A", status=Household.Status.ACTIVE
        )
        Household.objects.create(
            apartment="101", block="B", status=Household.Status.ARCHIVED
        )
        response = self.client.get(SEARCH_URL + "?apartment=101")
        self.assertEqual(response.status_code, 200)
        blocks = {h["block"] for h in response.data}
        self.assertIn("A", blocks)
        self.assertNotIn("B", blocks)


class HouseholdApprovalSmoke(BaseTestsUsers):
    def _signup_with_new_household(self):
        payload = _signup_payload()
        payload["household_request"] = {"apartment": "777", "block": "Z"}
        response = self.client.post(SIGNUP_URL, data=payload, format="json")
        return self.User.objects.get(pk=response.data["id"])

    def test_admin_approves_household_activates_user(self):
        user = self._signup_with_new_household()
        household = Household.objects.get(apartment="777", block="Z")

        self.authenticate(self.admin)
        response = self.client.post(_approve_url(household.id))
        self.assertEqual(response.status_code, 200, response.data)

        household.refresh_from_db()
        user.refresh_from_db()
        self.assertEqual(household.status, Household.Status.ACTIVE)
        self.assertTrue(user.is_active)

    def test_non_admin_cannot_approve(self):
        self._signup_with_new_household()
        household = Household.objects.get(apartment="777", block="Z")

        self.authenticate(self.user_a)
        response = self.client.post(_approve_url(household.id))
        self.assertEqual(response.status_code, 403)

    def test_admin_rejects_deletes_household_and_user(self):
        user = self._signup_with_new_household()
        household = Household.objects.get(apartment="777", block="Z")

        self.authenticate(self.admin)
        response = self.client.post(
            _reject_url(household.id), data={"reason": "denied"}, format="json"
        )
        self.assertEqual(response.status_code, 204)

        self.assertFalse(Household.objects.filter(pk=household.id).exists())
        self.assertFalse(self.User.objects.filter(pk=user.id).exists())


class MembershipFlowSmoke(BaseTestsUsers):
    def _seed_active_household(self):
        household = Household.objects.create(
            apartment="888", block="C", status=Household.Status.ACTIVE
        )
        HouseholdMembership.objects.create(
            household=household,
            user=self.user_a,
            role=HouseholdMembership.Role.HOLDER,
            status=HouseholdMembership.Status.ACTIVE,
        )
        return household

    def test_holder_approves_resident(self):
        household = self._seed_active_household()
        self.user_b.is_active = False
        self.user_b.save()
        membership = HouseholdMembership.objects.create(
            household=household,
            user=self.user_b,
            role=HouseholdMembership.Role.RESIDENT,
            status=HouseholdMembership.Status.PENDING_HOLDER,
        )

        self.authenticate(self.user_a)
        response = self.client.post(
            _membership_approve_url(household.id, membership.id)
        )
        self.assertEqual(response.status_code, 200, response.data)

        membership.refresh_from_db()
        self.user_b.refresh_from_db()
        self.assertEqual(
            membership.status, HouseholdMembership.Status.ACTIVE
        )
        self.assertTrue(self.user_b.is_active)

    def test_non_holder_cannot_approve(self):
        household = self._seed_active_household()
        membership = HouseholdMembership.objects.create(
            household=household,
            user=self.user_b,
            role=HouseholdMembership.Role.RESIDENT,
            status=HouseholdMembership.Status.PENDING_HOLDER,
        )

        self.authenticate(self.user_b)
        response = self.client.post(
            _membership_approve_url(household.id, membership.id)
        )
        self.assertEqual(response.status_code, 403)

    def test_holder_can_transfer_to_active_member(self):
        household = self._seed_active_household()
        HouseholdMembership.objects.create(
            household=household,
            user=self.user_b,
            role=HouseholdMembership.Role.RESIDENT,
            status=HouseholdMembership.Status.ACTIVE,
        )

        self.authenticate(self.user_a)
        response = self.client.post(
            _transfer_url(household.id),
            data={"to_user_id": self.user_b.id},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        b_membership = HouseholdMembership.objects.get(
            household=household, user=self.user_b
        )
        self.assertEqual(
            b_membership.role, HouseholdMembership.Role.HOLDER
        )


class PendingApprovalsSmoke(BaseTestsUsers):
    def test_anonymous_blocked(self):
        self.assertEqual(self.client.get(PENDING_URL).status_code, 401)

    def test_admin_sees_pending_admin_households(self):
        payload = _signup_payload()
        payload["household_request"] = {"apartment": "201", "block": "A"}
        self.client.post(SIGNUP_URL, data=payload, format="json")

        self.authenticate(self.admin)
        response = self.client.get(PENDING_URL)
        self.assertEqual(response.status_code, 200)
        statuses = {item["status"] for item in response.data}
        self.assertIn("PENDING_ADMIN", statuses)

    def test_holder_sees_only_pending_of_own_household(self):
        own = Household.objects.create(
            apartment="201", block="B", status=Household.Status.ACTIVE
        )
        HouseholdMembership.objects.create(
            household=own,
            user=self.user_a,
            role=HouseholdMembership.Role.HOLDER,
            status=HouseholdMembership.Status.ACTIVE,
        )
        HouseholdMembership.objects.create(
            household=own,
            user=self.user_b,
            role=HouseholdMembership.Role.RESIDENT,
            status=HouseholdMembership.Status.PENDING_HOLDER,
        )
        # noise: pending in a different household
        other = Household.objects.create(
            apartment="999", block="X", status=Household.Status.ACTIVE
        )
        HouseholdMembership.objects.create(
            household=other,
            user=self.admin,
            role=HouseholdMembership.Role.RESIDENT,
            status=HouseholdMembership.Status.PENDING_HOLDER,
        )

        self.authenticate(self.user_a)
        response = self.client.get(PENDING_URL)
        self.assertEqual(response.status_code, 200)
        household_ids = {item["household"]["id"] for item in response.data}
        self.assertEqual(household_ids, {own.id})

    def test_regular_user_without_holder_role_gets_empty(self):
        self.authenticate(self.user_b)
        response = self.client.get(PENDING_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])


class DependentsSmoke(BaseTestsUsers):
    def _seed_active_household(self):
        household = Household.objects.create(
            apartment="333", block="D", status=Household.Status.ACTIVE
        )
        HouseholdMembership.objects.create(
            household=household,
            user=self.user_a,
            role=HouseholdMembership.Role.HOLDER,
            status=HouseholdMembership.Status.ACTIVE,
        )
        return household

    def test_holder_creates_dependent(self):
        household = self._seed_active_household()
        self.authenticate(self.user_a)
        response = self.client.post(
            _dependents_url(household.id),
            data={
                "full_name": "Filho Silva",
                "birth_date": date(2012, 5, 1).isoformat(),
                "relationship": "filho",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["full_name"], "Filho Silva")

    def test_non_member_cannot_create(self):
        household = self._seed_active_household()
        self.authenticate(self.user_b)
        response = self.client.post(
            _dependents_url(household.id),
            data={
                "full_name": "Filho Silva",
                "birth_date": date(2012, 5, 1).isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_list_dependents_returns_active_only(self):
        household = self._seed_active_household()
        self.authenticate(self.user_a)
        self.client.post(
            _dependents_url(household.id),
            data={
                "full_name": "Filho Silva",
                "birth_date": date(2012, 5, 1).isoformat(),
            },
            format="json",
        )
        response = self.client.get(_dependents_url(household.id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
