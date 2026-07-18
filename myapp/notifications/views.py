"""Plain APIViews for in-app notifications."""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.serializers import (
    MarkAllReadOutputSerializer,
    NotificationOutputSerializer,
    PaginatedNotificationOutputSerializer,
    UnreadCountOutputSerializer,
)
from shared.container import container


@extend_schema(tags=["notifications"])
class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="unread",
                type=bool,
                location=OpenApiParameter.QUERY,
                required=False,
                description="When true, return only unread notifications.",
            ),
        ],
        responses={200: PaginatedNotificationOutputSerializer},
    )
    def get(self, request):
        unread_raw = (request.query_params.get("unread") or "").strip().lower()
        unread_only = unread_raw in {"1", "true", "yes"}
        queryset = container.notification_service.list_for(
            request.user, unread_only=unread_only
        )
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = NotificationOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


@extend_schema(tags=["notifications"])
class NotificationUnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: UnreadCountOutputSerializer})
    def get(self, request):
        count = container.notification_service.unread_count(request.user)
        return Response(UnreadCountOutputSerializer({"count": count}).data)


@extend_schema(tags=["notifications"])
class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses={200: NotificationOutputSerializer},
    )
    def patch(self, request, pk: int):
        instance = container.notification_service.mark_read(request.user, pk)
        return Response(NotificationOutputSerializer(instance).data)


@extend_schema(tags=["notifications"])
class NotificationMarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses={200: MarkAllReadOutputSerializer},
    )
    def post(self, request):
        updated = container.notification_service.mark_all_read(request.user)
        return Response(
            MarkAllReadOutputSerializer({"updated": updated}).data,
            status=status.HTTP_200_OK,
        )
