from rest_framework import serializers
from django.contrib.auth import get_user_model
from service_requests.models import ServiceRequestModel
from rest_framework.exceptions import ValidationError

class ServiceRequestSerializer(serializers.Serializer):
    
    PRIORITY_LEVEL = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    id = serializers.IntegerField(read_only=True)  
    requester_user = serializers.PrimaryKeyRelatedField(queryset = get_user_model().objects.all())
    title = serializers.CharField(max_length=150)
    request_description = serializers.CharField(required=False, allow_blank=True)
    service_type = serializers.CharField(max_length=150, default="Other")
    location = serializers.CharField(max_length=150, required=False, allow_blank=True)
    priority = serializers.ChoiceField(choices=PRIORITY_LEVEL, default='low')
    request_scheduled_date = serializers.DateTimeField()
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    # Staff will fill these fields
    responsable_staff = serializers.CharField(max_length=50, required = False)
    scheduled_date = serializers.DateTimeField(required = False)
    more_details = serializers.CharField(max_length=200, required = False)
    
    
    
    def create(self, validated_data):
        return ServiceRequestModel.objects.create(**validated_data)
    
    def update(self, instance, validated_data):
        if validated_data == {}:
            raise ValidationError('Invalid JSON')
        # Atualiza os campos da instância com os dados validados
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
    
    def to_representation(self, instance):
        # Adiciona a representação personalizada dos dados, incluindo o id
        representation = super().to_representation(instance)
        representation['id'] = instance.id
        return representation