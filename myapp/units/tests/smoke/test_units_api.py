"""Smoke tests for the units API."""

import pytest
from django.urls import reverse

from units.models import Unit, UnitMembership
from tests_base.base_tests_user import BaseTestsUsers


pytestmark = pytest.mark.api

LIST_URL = reverse("units:list")
PENDING_URL = reverse("units:pending-approvals")
HISTORY_URL = reverse("units:decision-history")


def _detail_url(pk):
    return reverse("units:detail", kwargs={"pk": pk})


def _memberships_list_url(pk):
    return reverse("units:memberships-list", kwargs={"pk": pk})


def _decisions_url(pk):
    return reverse("units:decisions-list", kwargs={"pk": pk})


def _membership_approve_url(pk, mid):
    return reverse("units:membership-approve", kwargs={"pk": pk, "mid": mid})


def _membership_reject_url(pk, mid):
    return reverse("units:membership-reject", kwargs={"pk": pk, "mid": mid})


def _ownership_transfer_url(pk, mid):
    return reverse("units:ownership-transfer", kwargs={"pk": pk, "mid": mid})


def _leave_url(pk):
    return reverse("units:leave", kwargs={"pk": pk})


class UnitPublicListSmoke(BaseTestsUsers):
    def test_public_list_returns_active_units_with_occupancy(self):
        vacant = Unit.objects.create(
            kind=Unit.Kind.APARTMENT,
            apartment="1",
            condominium=self.condominium,
            status=Unit.Status.ACTIVE,
        )
        occupied = Unit.objects.create(
            kind=Unit.Kind.APARTMENT,
            apartment="2",
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
            apartment="3",
            condominium=self.condominium,
            status=Unit.Status.ARCHIVED,
        )

        response = self.client.get(
            LIST_URL + f"?condominium_code={self.condominium.code}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["layout"], "flat")
        by_apartment = {
            item["apartment"]: item for item in response.data["units"]
        }
        self.assertEqual(set(by_apartment), {"1", "2"})
        self.assertFalse(by_apartment["1"]["is_occupied"])
        self.assertTrue(by_apartment["2"]["is_occupied"])

    def test_public_filters_lists_blocks_and_floors(self):
        Unit.objects.create(
            kind=Unit.Kind.APARTMENT_BLOCK,
            apartment="101",
            block="A",
            condominium=self.condominium,
            status=Unit.Status.ACTIVE,
        )
        Unit.objects.create(
            kind=Unit.Kind.APARTMENT_BLOCK,
            apartment="201",
            block="B",
            condominium=self.condominium,
            status=Unit.Status.ACTIVE,
        )
        response = self.client.get(
            reverse("units:filters")
            + f"?condominium_code={self.condominium.code}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["layout"], "blocks")
        self.assertEqual(response.data["filters"]["block"]["options"], ["A", "B"])
        self.assertEqual(response.data["filters"]["floor"]["options"], ["1", "2"])


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
        self.assertEqual(pending.data["count"], 1)
        self.assertEqual(len(pending.data["results"]), 1)

        # Legacy households path still works for old clients.
        legacy = self.client.get("/households/pending-approvals/")
        self.assertEqual(legacy.status_code, 200)
        self.assertEqual(legacy.data["count"], 1)

        approve = self.client.post(
            _membership_approve_url(unit.id, membership.id)
        )
        self.assertEqual(approve.status_code, 200)
        membership.refresh_from_db()
        self.assertEqual(membership.status, UnitMembership.Status.ACTIVE)

        decisions = self.client.get(_decisions_url(unit.id))
        self.assertEqual(decisions.status_code, 200)
        self.assertEqual(decisions.data["count"], 1)
        decision = decisions.data["results"][0]
        self.assertEqual(decision["action"], "APPROVED")
        self.assertEqual(decision["unit"]["id"], unit.id)
        self.assertEqual(decision["actor"]["id"], self.admin.id)
        self.assertEqual(decision["actor"]["role"], "ADMIN")
        self.assertEqual(decision["actor"]["email"], self.admin.email)
        self.assertTrue(decision["actor"]["full_name"])
        self.assertEqual(decision["target"]["id"], self.user_a.id)

        history = self.client.get(HISTORY_URL)
        self.assertEqual(history.status_code, 200)
        self.assertGreaterEqual(history.data["count"], 1)
        self.assertTrue(
            any(item["id"] == decision["id"] for item in history.data["results"])
        )

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
        self.assertEqual(pending.data["count"], 1)

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
        decisions = self.client.get(_decisions_url(unit.id))
        self.assertEqual(decisions.status_code, 200)
        decision = decisions.data["results"][0]
        self.assertEqual(decision["action"], "REJECTED")
        self.assertEqual(decision["reason"], "no")
        self.assertEqual(decision["target"]["id"], self.user_b.id)
        self.assertEqual(decision["actor"]["id"], self.user_a.id)
        self.assertEqual(decision["actor"]["role"], "OWNER")

        self.authenticate(self.user_b)
        forbidden = self.client.get(_decisions_url(unit.id))
        self.assertEqual(forbidden.status_code, 403)

    def test_decision_history_admin_only(self):
        self.authenticate(self.user_a)
        forbidden = self.client.get(HISTORY_URL)
        self.assertEqual(forbidden.status_code, 403)

        self.authenticate(self.admin)
        ok = self.client.get(HISTORY_URL)
        self.assertEqual(ok.status_code, 200)
        self.assertIn("results", ok.data)
        self.assertIn("count", ok.data)

        filtered = self.client.get(HISTORY_URL, {"action": "APPROVED"})
        self.assertEqual(filtered.status_code, 200)
        for item in filtered.data["results"]:
            self.assertEqual(item["action"], "APPROVED")

        bad = self.client.get(HISTORY_URL, {"action": "PENDING"})
        self.assertEqual(bad.status_code, 400)

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
        self.assertEqual(members.data["count"], 1)
        self.assertEqual(len(members.data["results"]), 1)

    def test_owner_transfers_ownership_to_resident(self):
        unit = Unit.objects.create(
            kind=Unit.Kind.APARTMENT,
            apartment="450",
            condominium=self.condominium,
            status=Unit.Status.ACTIVE,
        )
        previous_owner = UnitMembership.objects.create(
            unit=unit,
            user=self.user_a,
            role=UnitMembership.Role.OWNER,
            status=UnitMembership.Status.ACTIVE,
        )
        new_owner = UnitMembership.objects.create(
            unit=unit,
            user=self.user_b,
            role=UnitMembership.Role.RESIDENT,
            status=UnitMembership.Status.ACTIVE,
        )
        self.authenticate(self.user_a)

        response = self.client.post(
            _ownership_transfer_url(unit.id, new_owner.id)
        )

        self.assertEqual(response.status_code, 200, response.data)
        previous_owner.refresh_from_db()
        new_owner.refresh_from_db()
        self.assertEqual(previous_owner.role, UnitMembership.Role.RESIDENT)
        self.assertEqual(new_owner.role, UnitMembership.Role.OWNER)
        self.assertEqual(
            response.data["previous_owner"]["id"], previous_owner.id
        )
        self.assertEqual(response.data["new_owner"]["id"], new_owner.id)

    def test_resident_cannot_transfer_ownership(self):
        unit = Unit.objects.create(
            kind=Unit.Kind.APARTMENT,
            apartment="451",
            condominium=self.condominium,
            status=Unit.Status.ACTIVE,
        )
        UnitMembership.objects.create(
            unit=unit,
            user=self.user_a,
            role=UnitMembership.Role.OWNER,
            status=UnitMembership.Status.ACTIVE,
        )
        resident = UnitMembership.objects.create(
            unit=unit,
            user=self.user_b,
            role=UnitMembership.Role.RESIDENT,
            status=UnitMembership.Status.ACTIVE,
        )
        self.authenticate(self.user_b)

        response = self.client.post(
            _ownership_transfer_url(unit.id, resident.id)
        )

        self.assertEqual(response.status_code, 403)

    def test_resident_cannot_leave_unit(self):
        unit = Unit.objects.create(
            kind=Unit.Kind.APARTMENT,
            apartment="452",
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
            status=UnitMembership.Status.ACTIVE,
        )
        self.authenticate(self.user_b)

        response = self.client.post(_leave_url(unit.id))

        self.assertEqual(response.status_code, 403)
        membership.refresh_from_db()
        self.assertEqual(membership.status, UnitMembership.Status.ACTIVE)

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


BULK_URL = reverse("units:bulk-provision")


class UnitBulkProvisionSmoke(BaseTestsUsers):
    def test_superuser_provisions_chacon_style_blocks(self):
        # BaseTestsUsers.admin is created via create_superuser.
        self.authenticate(self.admin)
        response = self.client.post(
            BULK_URL,
            data={
                "condominium_code": self.condominium.code,
                "blocks": [
                    {"block": "A", "floors": 2, "units": ["01", "02"]},
                    {"block": "B", "floors": 1, "units": ["01"]},
                ],
                "named_units": ["Salão de Festas"],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["created_count"], 6)
        self.assertEqual(response.data["skipped_count"], 0)
        apartments = {
            (u["apartment"], u["block"]) for u in response.data["created"]
        }
        self.assertIn(("101", "A"), apartments)
        self.assertIn(("202", "A"), apartments)
        self.assertIn(("101", "B"), apartments)

    def test_staff_without_superuser_forbidden(self):
        from datetime import date

        from tests_base.base_tests_user import _gen_cpf

        staff = self.User.objects.create_user(
            username=f"{self.condominium.code}:condoadmin",
            email="condoadmin@example.com",
            password="Abcd123!",
            full_name="Condo Admin",
            birth_date=date(1985, 1, 1),
            cpf=_gen_cpf(),
            phone="11988887777",
            is_staff=True,
            is_superuser=False,
            role="ADMIN",
            condominium=self.condominium,
        )
        self.authenticate(staff)
        response = self.client.post(
            BULK_URL,
            data={
                "condominium_code": self.condominium.code,
                "blocks": [{"block": "A", "floors": 1, "units": ["01"]}],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_idempotent_skip_existing(self):
        self.authenticate(self.admin)
        payload = {
            "condominium_id": self.condominium.id,
            "blocks": [{"block": "Z", "floors": 1, "units": ["01", "02"]}],
        }
        first = self.client.post(BULK_URL, data=payload, format="json")
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(first.data["created_count"], 2)

        second = self.client.post(BULK_URL, data=payload, format="json")
        self.assertEqual(second.status_code, 201, second.data)
        self.assertEqual(second.data["created_count"], 0)
        self.assertEqual(second.data["skipped_count"], 2)
