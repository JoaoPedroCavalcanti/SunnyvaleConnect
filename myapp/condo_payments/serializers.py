"""Type/shape-only serializers for condo payments."""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from condo_payments.models import CondoPaymentModel


class CondoPaymentInputSerializer(serializers.Serializer):
    payer_user = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all(), required=True
    )
    title = serializers.CharField(max_length=150, required=True)
    status = serializers.ChoiceField(
        choices=CondoPaymentModel.STATUS, required=False, default="pending"
    )
    description = serializers.CharField(
        max_length=350, required=False, allow_blank=True, allow_null=True, default=""
    )
    payment_link = serializers.CharField(max_length=150, required=True)
    amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, default=0
    )
    due_date = serializers.DateField(required=False, allow_null=True)
    payment_date = serializers.DateTimeField(required=False, allow_null=True)


class CondoPaymentPatchSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=150, required=False)
    status = serializers.ChoiceField(choices=CondoPaymentModel.STATUS, required=False)
    description = serializers.CharField(
        max_length=350, required=False, allow_blank=True, allow_null=True
    )
    payment_link = serializers.CharField(max_length=150, required=False)
    amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )
    due_date = serializers.DateField(required=False, allow_null=True)
    payment_date = serializers.DateTimeField(required=False, allow_null=True)


class SetPaidStatusInputSerializer(serializers.Serializer):
    paid_payment_ids = serializers.ListField(child=serializers.IntegerField())


class CondoPaymentOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = CondoPaymentModel
        fields = "__all__"


class PaginatedCondoPaymentOutputSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = CondoPaymentOutputSerializer(many=True)
