"""Type/shape-only serializers for service requests.

The serializer layer never touches the DB and never embeds business
rules. It only validates payload *shape*. Authorization and "what fields
the user is allowed to write" live in the service.
"""

from rest_framework import serializers

from service_requests.models import ServiceRequestModel


class ServiceRequestInputSerializer(serializers.Serializer):
    """Payload a resident sends when opening a request.

    ``requester`` is intentionally NOT exposed — the service always
    pins it to ``request.user``. Admin-only fields (``status``,
    ``admin_response``, ``responded_by``) are not exposed either.
    """

    title = serializers.CharField(max_length=150, required=True)
    description = serializers.CharField(required=False, allow_blank=True)
    service_type = serializers.ChoiceField(
        choices=ServiceRequestModel.ServiceType.choices,
        default=ServiceRequestModel.ServiceType.OTHER,
        required=False,
    )
    location = serializers.CharField(
        max_length=150, required=False, allow_blank=True
    )
    priority = serializers.ChoiceField(
        choices=ServiceRequestModel.Priority.choices,
        default=ServiceRequestModel.Priority.LOW,
        required=False,
    )
    request_scheduled_date = serializers.DateTimeField(
        required=False, allow_null=True
    )


class ServiceRequestPatchSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=150, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    service_type = serializers.ChoiceField(
        choices=ServiceRequestModel.ServiceType.choices, required=False
    )
    location = serializers.CharField(
        max_length=150, required=False, allow_blank=True
    )
    priority = serializers.ChoiceField(
        choices=ServiceRequestModel.Priority.choices, required=False
    )
    request_scheduled_date = serializers.DateTimeField(
        required=False, allow_null=True
    )


class ServiceRequestRespondSerializer(serializers.Serializer):
    """Accept may carry an optional note; decline requires a justification."""

    action = serializers.ChoiceField(choices=["accept", "decline"])
    response = serializers.CharField(
        max_length=2000, required=False, allow_blank=True, default=""
    )

    def validate(self, attrs):
        action = attrs.get("action")
        response = (attrs.get("response") or "").strip()
        if action == "decline" and not response:
            raise serializers.ValidationError(
                {"response": "A justification is required when declining."}
            )
        attrs["response"] = response
        return attrs


class ServiceRequestOutputSerializer(serializers.ModelSerializer):
    requester = serializers.SerializerMethodField()
    responded_by = serializers.SerializerMethodField()

    class Meta:
        model = ServiceRequestModel
        fields = [
            "id",
            "title",
            "description",
            "service_type",
            "location",
            "priority",
            "status",
            "request_scheduled_date",
            "admin_response",
            "responded_by",
            "responded_at",
            "requester",
            "created_at",
            "updated_at",
        ]

    def get_requester(self, obj) -> dict | None:
        if not obj.requester_id:
            return None
        u = obj.requester
        return {
            "id": u.id,
            "username": u.username,
            "full_name": getattr(u, "full_name", ""),
            "apartment": getattr(u, "apartment", ""),
            "block": getattr(u, "block", ""),
        }

    def get_responded_by(self, obj) -> dict | None:
        if not obj.responded_by_id:
            return None
        u = obj.responded_by
        return {
            "id": u.id,
            "username": u.username,
            "full_name": getattr(u, "full_name", ""),
        }


class PaginatedServiceRequestOutputSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = ServiceRequestOutputSerializer(many=True)
