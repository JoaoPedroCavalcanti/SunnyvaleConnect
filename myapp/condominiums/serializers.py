"""Type/shape-only serializers for condominiums."""

from condominiums.models import Condominium
from rest_framework import serializers


class CondominiumInputSerializer(serializers.Serializer):
    name = serializers.CharField(required=True, max_length=150)
    primary_color = serializers.CharField(required=False, max_length=7, default="#d97706")
    secondary_color = serializers.CharField(
        required=False, max_length=7, default="#1e40af"
    )
    accent_color = serializers.CharField(required=False, max_length=7, default="#111827")
    logo = serializers.ImageField(required=False, allow_null=True)
    welcome_message = serializers.CharField(
        required=False, allow_blank=True, max_length=300, default=""
    )
    is_active = serializers.BooleanField(required=False, default=True)


class CondominiumLookupOutputSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Condominium
        fields = [
            "id",
            "name",
            "code",
            "primary_color",
            "secondary_color",
            "accent_color",
            "logo_url",
            "welcome_message",
        ]

    def get_logo_url(self, obj):
        if not obj.logo:
            return None
        request = self.context.get("request")
        if request is None:
            return obj.logo.url
        return request.build_absolute_uri(obj.logo.url)


class CondominiumOutputSerializer(CondominiumLookupOutputSerializer):
    class Meta(CondominiumLookupOutputSerializer.Meta):
        fields = CondominiumLookupOutputSerializer.Meta.fields + [
            "slug",
            "is_active",
            "created_at",
        ]
