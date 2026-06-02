"""Plain APIViews for households app."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from households.serializers import (
    DependentInputSerializer,
    DependentOutputSerializer,
    DependentPatchSerializer,
    HouseholdCreateRequestSerializer,
    HouseholdOutputSerializer,
    HouseholdRejectSerializer,
    MembershipOutputSerializer,
    MembershipRejectSerializer,
    MembershipTransferSerializer,
    PendingApprovalSerializer,
)
from shared.container import container


# ---- Households ----------------------------------------------------------- #
@extend_schema(tags=["households"])
class HouseholdSearchView(APIView):
    """Public search: filters by apartment/block to find which household to join."""

    permission_classes = [AllowAny]

    @extend_schema(responses={200: HouseholdOutputSerializer(many=True)})
    def get(self, request):
        apartment = request.query_params.get("apartment")
        block = request.query_params.get("block")
        results = container.household_service.search_public(apartment, block)
        serializer = HouseholdOutputSerializer(results, many=True)
        return Response(serializer.data)


@extend_schema(tags=["households"])
class HouseholdListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: HouseholdOutputSerializer(many=True)})
    def get(self, request):
        status_filter = request.query_params.get("status") or None
        queryset = container.household_service.list_for(
            request.user, status=status_filter
        )
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(list(queryset), request, view=self)
        serializer = HouseholdOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


@extend_schema(tags=["households"])
class HouseholdDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: HouseholdOutputSerializer})
    def get(self, request, pk: int):
        instance = container.household_service.get_for(request.user, pk)
        return Response(HouseholdOutputSerializer(instance).data)


@extend_schema(tags=["households"])
class HouseholdApproveView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(request=None, responses={200: HouseholdOutputSerializer})
    def post(self, request, pk: int):
        instance = container.household_service.approve(request.user, pk)
        return Response(HouseholdOutputSerializer(instance).data)


@extend_schema(tags=["households"])
class HouseholdRejectView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        request=HouseholdRejectSerializer,
        responses={204: None},
    )
    def post(self, request, pk: int):
        serializer = HouseholdRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        container.household_service.reject(
            request.user, pk, reason=serializer.validated_data.get("reason", "")
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---- Memberships --------------------------------------------------------- #
@extend_schema(tags=["households"])
class PendingApprovalsView(APIView):
    """Single endpoint, content depends on the caller:
    - admin → households waiting for admin approval
    - holder → residents waiting for holder approval in his household(s)
    - anyone else → empty list
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: PendingApprovalSerializer(many=True)})
    def get(self, request):
        items = container.membership_service.list_pending_approvals(request.user)
        return Response(PendingApprovalSerializer(items, many=True).data)


@extend_schema(tags=["households"])
class HouseholdMembershipListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: MembershipOutputSerializer(many=True)})
    def get(self, request, pk: int):
        memberships = container.membership_service.list_for_household(
            request.user, pk
        )
        serializer = MembershipOutputSerializer(memberships, many=True)
        return Response(serializer.data)


@extend_schema(tags=["households"])
class MembershipApproveView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={200: MembershipOutputSerializer})
    def post(self, request, pk: int, mid: int):
        instance = container.membership_service.approve(request.user, mid)
        return Response(MembershipOutputSerializer(instance).data)


@extend_schema(tags=["households"])
class MembershipRejectView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=MembershipRejectSerializer,
        responses={204: None},
    )
    def post(self, request, pk: int, mid: int):
        serializer = MembershipRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        container.membership_service.reject(
            request.user, mid, reason=serializer.validated_data.get("reason", "")
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["households"])
class MembershipPromoteView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={200: MembershipOutputSerializer})
    def post(self, request, pk: int, mid: int):
        instance = container.membership_service.promote(request.user, mid)
        return Response(MembershipOutputSerializer(instance).data)


@extend_schema(tags=["households"])
class MembershipDemoteView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={200: MembershipOutputSerializer})
    def post(self, request, pk: int, mid: int):
        instance = container.membership_service.demote(request.user, mid)
        return Response(MembershipOutputSerializer(instance).data)


@extend_schema(tags=["households"])
class MembershipRemoveView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={204: None})
    def delete(self, request, pk: int, mid: int):
        container.membership_service.remove(request.user, mid)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["households"])
class HouseholdLeaveView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={204: None})
    def post(self, request, pk: int):
        container.membership_service.leave(request.user, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["households"])
class HouseholdTransferView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=MembershipTransferSerializer,
        responses={200: MembershipOutputSerializer},
    )
    def post(self, request, pk: int):
        serializer = MembershipTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = container.membership_service.transfer(
            request.user, pk, serializer.validated_data["to_user_id"]
        )
        return Response(MembershipOutputSerializer(instance).data)


# ---- Dependents ---------------------------------------------------------- #
@extend_schema(tags=["households"])
class DependentListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: DependentOutputSerializer(many=True)})
    def get(self, request, pk: int):
        dependents = container.dependent_service.list_for_household(
            request.user, pk
        )
        return Response(
            DependentOutputSerializer(dependents, many=True).data
        )

    @extend_schema(
        request=DependentInputSerializer,
        responses={201: DependentOutputSerializer},
    )
    def post(self, request, pk: int):
        serializer = DependentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = container.dependent_service.create(
            request.user, pk, serializer.validated_data
        )
        return Response(
            DependentOutputSerializer(instance).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["households"])
class DependentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=DependentPatchSerializer,
        responses={200: DependentOutputSerializer},
    )
    def patch(self, request, pk: int, did: int):
        serializer = DependentPatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = container.dependent_service.update(
            request.user, did, serializer.validated_data
        )
        return Response(DependentOutputSerializer(instance).data)

    @extend_schema(responses={204: None})
    def delete(self, request, pk: int, did: int):
        container.dependent_service.delete(request.user, did)
        return Response(status=status.HTTP_204_NO_CONTENT)
