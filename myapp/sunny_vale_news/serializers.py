"""Type/shape-only serializers for SunnyValeNews."""

from rest_framework import serializers

from sunny_vale_news.models import SunnyValeNewsModel


class SunnyValeNewsInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200, required=True)
    description = serializers.CharField(required=True)
    author = serializers.CharField(max_length=50, required=True)
    priority_level = serializers.ChoiceField(
        choices=SunnyValeNewsModel.PRIORITY, required=False, default="low"
    )


class SunnyValeNewsPatchSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False)
    author = serializers.CharField(max_length=50, required=False)
    priority_level = serializers.ChoiceField(
        choices=SunnyValeNewsModel.PRIORITY, required=False
    )


class SunnyValeNewsOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = SunnyValeNewsModel
        fields = "__all__"
