"""Smoke tests for the units API."""

import pytest
from django.urls import reverse

from units.models import Unit, UnitMembership
from tests_base.base_tests_user import BaseTestsUsers


pytestmark = pytest.mark.api

LIST_URL = reverse("units:list")
PENDING_URL = reverse("units:pending-approvals")


def _detail_url(pk):
    return reverse("units:detail", kwargs={"pk": pk})


def _memberships_list_url(pk):
    return reverse("units:memberships-list", kwargs={"pk": pk})


def _membership_approve_url(pk, mid):
    return reverse("units:membership-approve", kwargs={"pk": pk, "mid": mid})


def _membership_reject_url(pk, mid):
    return reverse("units:membership-reject", kwargs={"pk": pk, "mid": mid})


def _leave_url(pk):
    return reverse("units:leave", kwargs={"pk": pk})


class UnitPublicListSmoke(BaseTestsUsers):
    def test_public_list_returns_active_units_with_occupancy(self):
        vacant = Unit.objects.create(
            kind=Unit.Kind.APARTMENT,
            apartment="101",
            condominium=self.condominium,
            status=Unit.Status.ACTIVE,
        )
        occupied = Unit.objects.create(
            kind=Unit.Kind.APARTMENT,
            apartment="102",
            condominium=self.condominium,
            status=Unit.Status.ACTIVE,
        )
        UnitMembership.objects.create(
            unit=occupied,
            user=self.user_a,
            role=UnitMembership.Role.OWNER,
            status=UnitMembership.Status.ACTIVE,
        )
        Unit.objects.create(
            kind=Unit.Kind.APARTMENT,
            apartment="103",
            condominium=self.condominium,
            status=Unit.Status.ARCHIVED,
        )

        response = self.client.get(
            LIST_URL + f"?condominium_code={self.condominium.code}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        by_apartment = {item["apartment"]: item for item in response.data}
        self.assertFalse(by_apartment["101"]["is_occupied"])
        self.assertTrue(by_apartment["102"]["is_occupied"])
        self.assertNotIn("103", by_apartment)


class UnitAdminCreateSmoke(BaseTestsUsers):
    def test_admin_creates_unit(self):
        self.authenticate(self.admin)
        response = self.client.post(
            LIST_URL,
            data={"kind": Unit.Kind.APARTMENT, "apartment": "501"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["apartment"], "501")
        self.assertEqual(response.data["status"], Unit.Status.ACTIVE)

    def test_non_admin_cannot_create(self):
        self.authenticate(self.user_a)
        response = self.client.post(
            LIST_URL,
            data={"kind": Unit.Kind.APARTMENT, "apartment": "502"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)


class UnitAuthListSmoke(BaseTestsUsers):
    def test_member_sees_own_unit(self):
        unit = Unit.objects.create(
            kind=Unit.Kind.APARTMENT,
            apartment="201",
            condominium=self.condominium,
            status=Unit.Status.ACTIVE,
        )
        UnitMembership.objects.create(
            unit=unit,
            user=self.user_a,
            role=UnitMembership.Role.OWNER,
            status=UnitMembership.Status.ACTIVE,
        )
        self.authenticate(self.user_a)
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        results = response.data["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["apartment"], "201")
        self.assertEqual(len(results[0]["members"]), 1)


class UnitMembershipFlowSmoke(BaseTestsUsers):
    def test_join_vacant_unit_and_admin_approve(self):
        unit = Unit.objects.create(
            kind=Unit.Kind.APARTMENT,
            apartment="301",
            condominium=self.condominium,
            status=Unit.Status.ACTIVE,
        )
        self.authenticate(self.user_a)
        membership = UnitMembership.objects.create(
            unit=unit,
            user=self.user_a,
            role=UnitMembership.Role.OWNER,
            status=UnitMembership.Status.PENDING_ADMIN,
        )

        self.authenticate(self.admin)
        pending = self.client.get(PENDING_URL)
        self.assertEqual(pending.status_code, 200)
        self.assertEqual(len(pending.data), 1)

        approve = self.client.post(
            _membership_approve_url(unit.id, membership.id)
        )
        self.assertEqual(approve.status_code, 200)
        membership.refresh_from_db()
        self.assertEqual(membership.status, UnitMembership.Status.ACTIVE)

    def test_join_occupied_unit_and_owner_approve(self):
        unit = Unit.objects.create(
            kind=Unit.Kind.APARTMENT,
            apartment="401",
            condominium=self.condominium,
            status=Unit.Status.ACTIVE,
        )
        UnitMembership.objects.create(
            unit=unit,
            user=self.user_a,
            role=UnitMembership.Role.OWNER,
            status=UnitMembership.Status.ACTIVE,
        )
        membership = UnitMembership.objects.create(
            unit=unit,
            user=self.user_b,
            role=UnitMembership.Role.RESIDENT,
            status=UnitMembership.Status.PENDING_OWNER,
        )

        self.authenticate(self.user_a)
        pending = self.client.get(PENDING_URL)
        self.assertEqual(len(pending.data), 1)

        approve = self.client.post(
            _membership_approve_url(unit.id, membership.id)
        )
        self.assertEqual(approve.status_code, 200)
        membership.refresh_from_db()
        self.assertEqual(membership.status, UnitMembership.Status.ACTIVE)

    def test_owner_rejects_resident(self):
        unit = Unit.objects.create(
            kind=Unit.Kind.APARTMENT,
            apartment="402",
            condominium=self.condominium,
            status=Unit.Status.ACTIVE,
        )
        UnitMembership.objects.create(
            unit=unit,
            user=self.user_a,
            role=UnitMembership.Role.OWNER,
            status=UnitMembership.Status.ACTIVE,
        )
        membership = UnitMembership.objects.create(
            unit=unit,
            user=self.user_b,
            role=UnitMembership.Role.RESIDENT,
            status=UnitMembership.Status.PENDING_OWNER,
        )

        self.authenticate(self.user_a)
        response = self.client.post(
            _membership_reject_url(unit.id, membership.id),
            data={"reason": "no"},
            format="json",
        )
        self.assertEqual(response.status_code, 204)
        self.assertFalse(
            UnitMembership.objects.filter(pk=membership.id).exists()
        )

    def test_detail_and_memberships_list(self):
        unit = Unit.objects.create(
            kind=Unit.Kind.NAMED,
            name="Pool House",
            condominium=self.condominium,
            status=Unit.Status.ACTIVE,
        )
        UnitMembership.objects.create(
            unit=unit,
            user=self.user_a,
            role=UnitMembership.Role.OWNER,
            status=UnitMembership.Status.ACTIVE,
        )
        self.authenticate(self.user_a)
        detail = self.client.get(_detail_url(unit.id))
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["display_name"], "Pool House")

        members = self.client.get(_memberships_list_url(unit.id))
        self.assertEqual(members.status_code, 200)
        self.assertEqual(len(members.data), 1)

    def test_leave_archives_empty_unit(self):
        unit = Unit.objects.create(
            kind=Unit.Kind.APARTMENT,
            apartment="501",
            condominium=self.condominium,
            status=Unit.Status.ACTIVE,
        )
        UnitMembership.objects.create(
            unit=unit,
            user=self.user_a,
            role=UnitMembership.Role.OWNER,
            status=UnitMembership.Status.ACTIVE,
        )
        self.authenticate(self.user_a)
        response = self.client.post(_leave_url(unit.id))
        self.assertEqual(response.status_code, 204)
        unit.refresh_from_db()
        self.assertEqual(unit.status, Unit.Status.ARCHIVED)
