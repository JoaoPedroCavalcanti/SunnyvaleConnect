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
    HouseholdWithMembersOutputSerializer,
    MembershipDecisionOutputSerializer,
    MembershipOutputSerializer,
    MembershipRejectSerializer,
    MembershipTransferSerializer,
    PendingApprovalSerializer,
    ResidentItemSerializer,
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
        condominium_code = request.query_params.get("condominium_code", "")
        results = container.household_service.search_public(
            condominium_code, apartment, block
        )
        serializer = HouseholdOutputSerializer(results, many=True)
        return Response(serializer.data)


@extend_schema(tags=["households"])
class HouseholdListView(APIView):
    """List households scoped to the caller.

    - Admin: every household.
    - Regular user: only the households the user is an active member of.

    Each item embeds the active members so the front can render a
    household card without an extra request per row. Reservations,
    payments and similar bundles will be appended here too.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: HouseholdWithMembersOutputSerializer(many=True)}
    )
    def get(self, request):
        status_filter = request.query_params.get("status") or None
        items = container.household_service.list_for_with_members(
            request.user, status=status_filter
        )
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(items, request, view=self)
        serializer = HouseholdWithMembersOutputSerializer(page, many=True)
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


# ---- Decisions (audit log) ---------------------------------------------- #
@extend_schema(tags=["households"])
class HouseholdDecisionListView(APIView):
    """Audit log of every approve/reject performed by a holder (or admin)
    over resident requests for this household.

    Permission: active holder of the household, or admin. Residents
    don't see the log (it can include reject reasons).
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: MembershipDecisionOutputSerializer(many=True)}
    )
    def get(self, request, pk: int):
        items = container.membership_decision_service.list_for_household(
            request.user, pk
        )
        return Response(
            MembershipDecisionOutputSerializer(items, many=True).data
        )


# ---- Dependents ---------------------------------------------------------- #
@extend_schema(tags=["households"])
class DependentListCreateView(APIView):
    """Detail-of-a-house list: active household members first
    (``type="household"``) and active dependents after
    (``type="dependent"``).

    Permission: active member of the household, or admin.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: ResidentItemSerializer(many=True)})
    def get(self, request, pk: int):
        items = container.dependent_service.list_residents(request.user, pk)
        return Response(ResidentItemSerializer(items, many=True).data)

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
