"""Type/shape-only serializers for households app."""

from rest_framework import serializers

from households.models import (
    Dependent,
    Household,
    HouseholdMembership,
    MembershipDecision,
)


# ---- Household ------------------------------------------------------- #
class HouseholdCreateRequestSerializer(serializers.Serializer):
    apartment = serializers.CharField(required=True, max_length=10)
    block = serializers.CharField(
        required=False, allow_blank=True, max_length=10, default=""
    )


class HouseholdOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Household
        fields = ["id", "apartment", "block", "status", "created_at"]


class HouseholdRejectSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


# ---- Membership ------------------------------------------------------ #
class MembershipUserSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    cpf = serializers.CharField(read_only=True)
    phone = serializers.CharField(read_only=True)


class MembershipOutputSerializer(serializers.ModelSerializer):
    user = MembershipUserSerializer(read_only=True)

    class Meta:
        model = HouseholdMembership
        fields = [
            "id",
            "household",
            "user",
            "role",
            "status",
            "joined_at",
            "left_at",
        ]


class PendingApprovalSerializer(serializers.ModelSerializer):
    """Membership awaiting approval, with the household inlined.

    Used by the unified ``/households/pending-approvals/`` endpoint so the
    front can render both admin-pending and holder-pending in the same list
    without an extra request per row.
    """

    user = MembershipUserSerializer(read_only=True)
    household = HouseholdOutputSerializer(read_only=True)

    class Meta:
        model = HouseholdMembership
        fields = [
            "id",
            "household",
            "user",
            "role",
            "status",
            "joined_at",
        ]


class MembershipTransferSerializer(serializers.Serializer):
    to_user_id = serializers.IntegerField(required=True)


class MembershipRejectSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class MembershipDecisionOutputSerializer(serializers.ModelSerializer):
    """Audit row payload. Snapshots are exposed under ``actor`` and
    ``target`` sub-objects so the front can render even after the
    underlying users or household get deleted (FKs are nullable)."""

    actor = serializers.SerializerMethodField()
    target = serializers.SerializerMethodField()

    class Meta:
        model = MembershipDecision
        fields = [
            "id",
            "household",
            "household_apartment",
            "household_block",
            "actor",
            "target",
            "action",
            "reason",
            "created_at",
        ]

    def get_actor(self, obj) -> dict:
        return {
            "id": obj.actor_id,
            "username": obj.actor_username,
            "full_name": obj.actor_full_name,
        }

    def get_target(self, obj) -> dict:
        return {
            "id": obj.target_id,
            "username": obj.target_username,
            "full_name": obj.target_full_name,
            "email": obj.target_email,
        }


class HouseholdWithMembersOutputSerializer(serializers.Serializer):
    """Rich household payload for listings: ``HouseholdOutputSerializer``
    fields plus ``members`` (active memberships only).

    Input is the dict produced by
    ``HouseholdService.list_for_with_members``: ``{"household", "members"}``.
    """

    def to_representation(self, instance):
        household = instance["household"]
        members = instance.get("members") or []
        data = HouseholdOutputSerializer(household).data
        data["members"] = MembershipOutputSerializer(members, many=True).data
        return data


# ---- Dependent ------------------------------------------------------- #
class DependentInputSerializer(serializers.Serializer):
    full_name = serializers.CharField(required=True, max_length=150)
    birth_date = serializers.DateField(required=True)
    cpf = serializers.CharField(
        required=False, allow_blank=True, max_length=14, default=""
    )
    relationship = serializers.CharField(
        required=False, allow_blank=True, max_length=50, default=""
    )


class DependentPatchSerializer(serializers.Serializer):
    full_name = serializers.CharField(required=False, max_length=150)
    birth_date = serializers.DateField(required=False)
    cpf = serializers.CharField(required=False, allow_blank=True, max_length=14)
    relationship = serializers.CharField(
        required=False, allow_blank=True, max_length=50
    )


class DependentOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dependent
        fields = [
            "id",
            "household",
            "full_name",
            "birth_date",
            "cpf",
            "relationship",
            "is_active",
            "created_at",
        ]


class ResidentItemSerializer(serializers.Serializer):
    """Polymorphic item for the ``/dependents/`` listing.

    Active household members are emitted first with ``type="household"``
    (payload identical to ``MembershipOutputSerializer``), followed by
    active dependents with ``type="dependent"`` (payload identical to
    ``DependentOutputSerializer``).

    Input is the dict produced by ``DependentService.list_residents``:
    ``{"type": "household"|"dependent", "obj": <instance>}``.
    """

    def to_representation(self, instance):
        item_type = instance["type"]
        obj = instance["obj"]
        if item_type == "household":
            return {"type": "household", **MembershipOutputSerializer(obj).data}
        if item_type == "dependent":
            return {"type": "dependent", **DependentOutputSerializer(obj).data}
        raise ValueError(f"Unknown resident item type: {item_type!r}")


# ---- Signup (household_request piece) -------------------------------- #
class HouseholdRequestSerializer(serializers.Serializer):
    """Embedded inside the signup payload to declare household intent.

    Exactly one of (household_id) OR (apartment) is required.
    """

    household_id = serializers.IntegerField(required=False, allow_null=True)
    apartment = serializers.CharField(
        required=False, allow_blank=True, max_length=10
    )
    block = serializers.CharField(
        required=False, allow_blank=True, max_length=10, default=""
    )
