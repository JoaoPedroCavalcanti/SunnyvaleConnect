"""Plain APIViews for visitor access."""

from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from shared.container import container
from visitor_access.serializers import (
    VisitorAccessInputSerializer,
    VisitorAccessOutputSerializer,
    VisitorGroupInputSerializer,
    VisitorGroupOutputSerializer,
    VisitorGroupPatchSerializer,
    VisitorGroupScheduleInputSerializer,
)


_CheckinResponse = inline_serializer(
    name="CheckinResponse",
    fields={"checkin_code": serializers.CharField()},
)
_CheckoutResponse = inline_serializer(
    name="CheckoutResponse",
    fields={"checkout_code": serializers.CharField()},
)


@extend_schema(tags=["visitor_access"])
class VisitorAccessListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: VisitorAccessOutputSerializer(many=True)})
    def get(self, request):
        queryset = container.visitor_access_service.list_for(request.user)
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = VisitorAccessOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        request=VisitorAccessInputSerializer,
        responses={201: VisitorAccessOutputSerializer},
    )
    def post(self, request):
        serializer = VisitorAccessInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = container.visitor_access_service.create(
            request.user, serializer.validated_data
        )
        return Response(
            VisitorAccessOutputSerializer(instance).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["visitor_access"])
class VisitorAccessDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: VisitorAccessOutputSerializer})
    def get(self, request, pk: int):
        instance = container.visitor_access_service.get_for(request.user, pk)
        return Response(VisitorAccessOutputSerializer(instance).data)

    @extend_schema(responses={204: None})
    def delete(self, request, pk: int):
        container.visitor_access_service.delete(request.user, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["visitor_access"])
class VisitorAccessCheckinView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        responses={
            200: OpenApiResponse(
                response=_CheckinResponse,
                description="Returns the check-in code, or a plain text message "
                "when the request is outside the allowed window.",
            )
        }
    )
    def get(self, request, visitor_access_link_checkin: str):
        result = container.visitor_access_service.checkin(visitor_access_link_checkin)
        return Response(result)


@extend_schema(tags=["visitor_access"])
class VisitorGroupListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: VisitorGroupOutputSerializer(many=True)})
    def get(self, request):
        queryset = container.visitor_group_service.list_for(request.user)
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = VisitorGroupOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        request=VisitorGroupInputSerializer,
        responses={201: VisitorGroupOutputSerializer},
    )
    def post(self, request):
        serializer = VisitorGroupInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = container.visitor_group_service.create(
            request.user, serializer.validated_data
        )
        return Response(
            VisitorGroupOutputSerializer(instance).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["visitor_access"])
class VisitorGroupDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: VisitorGroupOutputSerializer})
    def get(self, request, pk: int):
        instance = container.visitor_group_service.get_for(request.user, pk)
        return Response(VisitorGroupOutputSerializer(instance).data)

    @extend_schema(
        request=VisitorGroupPatchSerializer,
        responses={200: VisitorGroupOutputSerializer},
    )
    def patch(self, request, pk: int):
        serializer = VisitorGroupPatchSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = container.visitor_group_service.update(
            request.user, pk, serializer.validated_data
        )
        return Response(VisitorGroupOutputSerializer(instance).data)

    @extend_schema(responses={204: None})
    def delete(self, request, pk: int):
        container.visitor_group_service.delete(request.user, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["visitor_access"])
class VisitorGroupScheduleView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=VisitorGroupScheduleInputSerializer,
        responses={201: VisitorAccessOutputSerializer(many=True)},
    )
    def post(self, request, pk: int):
        serializer = VisitorGroupScheduleInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        visits = container.visitor_group_service.schedule_visit(
            request.user, pk, serializer.validated_data
        )
        return Response(
            VisitorAccessOutputSerializer(visits, many=True).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["visitor_access"])
class VisitorAccessCheckoutView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        responses={
            200: OpenApiResponse(
                response=_CheckoutResponse,
                description="Returns the check-out code if inside the allowed window.",
            )
        }
    )
    def get(self, request, visitor_access_link_checkout: str):
        result = container.visitor_access_service.checkout(
            visitor_access_link_checkout
        )
        return Response(result)
