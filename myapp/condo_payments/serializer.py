from rest_framework.serializers import ModelSerializer
from condo_payments.models import CondoPaymentModel


class CondoPaymentSerializer(ModelSerializer):
    class Meta:
        model = CondoPaymentModel
        fields = "__all__"
