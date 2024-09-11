from sunny_vale_news.models import SunnyValeNewsModel
from rest_framework.serializers import ModelSerializer

class SunnyValeNewsSerializer(ModelSerializer):
    class Meta:
        model = SunnyValeNewsModel
        fields = '__all__'
        extra_kwargs = {
            'title': {'required': True},
            'description': {'required': True},
            'author': {'required': True},
            }