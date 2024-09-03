from rest_framework.serializers import ModelSerializer
from visitor_access.models import VisitorAccessModel

class VisitorAccessSerializer(ModelSerializer):
    class Meta:
        model = VisitorAccessModel
        fields = '__all__'