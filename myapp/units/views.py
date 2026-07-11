"""Plain APIViews for units app."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from units.serializers import (
    PendingUnitApprovalSerializer,
    UnitBulkProvisionInputSerializer,
    UnitBulkProvisionOutputSerializer,
    UnitCreateInputSerializer,
    UnitMembershipOutputSerializer,
    UnitMembershipRejectSerializer,
    UnitOutputSerializer,
    UnitPublicOutputSerializer,
    UnitWithMembersOutputSerializer,
)
from shared.container import container
from shared.permissions import IsPlatformSuperuser


@extend_schema(tags=["units"])
class UnitBulkProvisionView(APIView):
    """Platform superuser only: expand block/floor recipes into units."""

    permission_classes = [IsPlatformSuperuser]

    @extend_schema(
        request=UnitBulkProvisionInputSerializer,
        responses={201: UnitBulkProvisionOutputSerializer},
    )
    def post(self, request):
        serializer = UnitBulkProvisionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = container.unit_service.bulk_provision(
            request.user, serializer.validated_data
        )
        return Response(
            UnitBulkProvisionOutputSerializer(result).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["units"])
class UnitListCreateView(APIView):
    """GET public list (``?condominium_code=``) or authenticated scoped list.

    POST creates a unit (admin only).
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdminUser()]
        if self.request.user.is_authenticated:
            return [IsAuthenticated()]
        return [AllowAny()]

    @extend_schema(responses={200: UnitPublicOutputSerializer(many=True)})
    def get(self, request):
        if request.user.is_authenticated:
            status_filter = request.query_params.get("status") or None
            items = container.unit_service.list_for_with_members(
                request.user, status=status_filter
            )
            paginator = PageNumberPagination()
            page = paginator.paginate_queryset(items, request, view=self)
            serializer = UnitWithMembersOutputSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        condominium_code = request.query_params.get("condominium_code", "")
        items = container.unit_service.list_public(condominium_code)
        serializer = UnitPublicOutputSerializer(items, many=True)
        return Response(serializer.data)

    @extend_schema(
        request=UnitCreateInputSerializer,
        responses={201: UnitOutputSerializer},
    )
    def post(self, request):
        serializer = UnitCreateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = container.unit_service.create(
            request.user, serializer.validated_data
        )
        return Response(
            UnitOutputSerializer(instance).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["units"])
class UnitDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: UnitOutputSerializer})
    def get(self, request, pk: int):
        instance = container.unit_service.get_for(request.user, pk)
        return Response(UnitOutputSerializer(instance).data)


@extend_schema(tags=["units"])
class PendingApprovalsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: PendingUnitApprovalSerializer(many=True)})
    def get(self, request):
        items = container.unit_membership_service.list_pending_approvals(
            request.user
        )
        return Response(PendingUnitApprovalSerializer(items, many=True).data)


@extend_schema(tags=["units"])
class UnitMembershipListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: UnitMembershipOutputSerializer(many=True)})
    def get(self, request, pk: int):
        memberships = container.unit_membership_service.list_for_unit(
            request.user, pk
        )
        serializer = UnitMembershipOutputSerializer(memberships, many=True)
        return Response(serializer.data)


@extend_schema(tags=["units"])
class UnitMembershipApproveView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={200: UnitMembershipOutputSerializer})
    def post(self, request, pk: int, mid: int):
        instance = container.unit_membership_service.approve(request.user, mid)
        return Response(UnitMembershipOutputSerializer(instance).data)


@extend_schema(tags=["units"])
class UnitMembershipRejectView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=UnitMembershipRejectSerializer,
        responses={204: None},
    )
    def post(self, request, pk: int, mid: int):
        serializer = UnitMembershipRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        container.unit_membership_service.reject(
            request.user, mid, reason=serializer.validated_data.get("reason", "")
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["units"])
class UnitMembershipRemoveView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={204: None})
    def delete(self, request, pk: int, mid: int):
        container.unit_membership_service.remove(request.user, mid)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["units"])
class UnitLeaveView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={204: None})
    def post(self, request, pk: int):
        container.unit_membership_service.leave(request.user, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)
