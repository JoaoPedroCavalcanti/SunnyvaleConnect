"""Type/shape-only serializers for users."""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from households.serializers import HouseholdRequestSerializer


class UserInputSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)
    full_name = serializers.CharField(required=True, max_length=150)
    birth_date = serializers.DateField(required=True)
    cpf = serializers.CharField(required=True, max_length=14)
    phone = serializers.CharField(required=True, max_length=20)
    email = serializers.EmailField(required=True)
    photo = serializers.ImageField(required=False, allow_null=True)
    household_request = HouseholdRequestSerializer(required=False, allow_null=True)


class UserPatchSerializer(serializers.Serializer):
    """CPF and username are immutable after creation."""

    password = serializers.CharField(required=False, write_only=True)
    full_name = serializers.CharField(required=False, max_length=150)
    birth_date = serializers.DateField(required=False)
    phone = serializers.CharField(required=False, max_length=20)
    email = serializers.EmailField(required=False)
    apartment = serializers.CharField(required=False, max_length=10)
    block = serializers.CharField(required=False, allow_blank=True, max_length=10)
    photo = serializers.ImageField(required=False, allow_null=True)


class UserOutputSerializer(serializers.ModelSerializer):
    photo = serializers.ImageField(read_only=True)

    class Meta:
        model = get_user_model()
        fields = [
            "id",
            "username",
            "full_name",
            "birth_date",
            "cpf",
            "phone",
            "email",
            "apartment",
            "block",
            "photo",
        ]


class LoginInputSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)


class LoginOutputSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)
