"""Type/shape-only serializers for SunnyValeNews."""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from sunny_vale_news.models import SunnyValeNewsModel


class NewsAuthorSerializer(serializers.Serializer):
    """Authorship snapshot embedded inside news listings.

    ``id`` is null when the original author user has been deleted; in
    that case the front falls back to rendering only ``full_name``.
    """

    id = serializers.IntegerField(allow_null=True, read_only=True)
    full_name = serializers.CharField(read_only=True)
    role = serializers.CharField(read_only=True, allow_blank=True)


class SunnyValeNewsInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200, required=True)
    description = serializers.CharField(required=True)
    kind = serializers.ChoiceField(
        choices=SunnyValeNewsModel.Kind.choices,
        required=False,
        default=SunnyValeNewsModel.Kind.NOTICE,
    )
    priority_level = serializers.ChoiceField(
        choices=SunnyValeNewsModel.PRIORITY, required=False, default="low"
    )


class SunnyValeNewsPatchSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False)
    kind = serializers.ChoiceField(
        choices=SunnyValeNewsModel.Kind.choices, required=False
    )
    priority_level = serializers.ChoiceField(
        choices=SunnyValeNewsModel.PRIORITY, required=False
    )


class SunnyValeNewsOutputSerializer(serializers.ModelSerializer):
    """Listing/detail payload.

    ``created_by`` exposes the authorship denormalized snapshot
    (``author`` / ``author_role``) under a single object so the front
    can render "criado por João Pedro · Administrador" with one line of
    JSX. ``id`` inside ``created_by`` is null when the original author
    has been deleted (FK is nullable).
    """

    created_by = serializers.SerializerMethodField()

    class Meta:
        model = SunnyValeNewsModel
        fields = [
            "id",
            "title",
            "description",
            "kind",
            "priority_level",
            "created_by",
            "created_at",
            "updated_at",
        ]

    @extend_schema_field(NewsAuthorSerializer)
    def get_created_by(self, obj):
        return NewsAuthorSerializer(
            {
                "id": obj.created_by_id,
                "full_name": obj.author,
                "role": obj.author_role,
            }
        ).data
