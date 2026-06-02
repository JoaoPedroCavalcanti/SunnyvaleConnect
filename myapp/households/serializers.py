"""Type/shape-only serializers for households app."""

from rest_framework import serializers

from households.models import Dependent, Household, HouseholdMembership


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
