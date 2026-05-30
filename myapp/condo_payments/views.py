"""Plain APIViews for condo payments."""

from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from condo_payments.serializers import (
    CondoPaymentInputSerializer,
    CondoPaymentOutputSerializer,
    CondoPaymentPatchSerializer,
    SetPaidStatusInputSerializer,
)
from shared.container import container


class CondoPaymentListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = container.condo_payment_service.list_for(request.user)
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = CondoPaymentOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = CondoPaymentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = container.condo_payment_service.create(
            request.user, serializer.validated_data
        )
        return Response(
            CondoPaymentOutputSerializer(instance).data, status=status.HTTP_201_CREATED
        )


class CondoPaymentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk: int):
        instance = container.condo_payment_service.get_for(request.user, pk)
        return Response(CondoPaymentOutputSerializer(instance).data)

    def put(self, request, pk: int):
        serializer = CondoPaymentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = container.condo_payment_service.update(
            request.user, pk, serializer.validated_data
        )
        return Response(CondoPaymentOutputSerializer(instance).data)

    def patch(self, request, pk: int):
        serializer = CondoPaymentPatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = container.condo_payment_service.update(
            request.user, pk, serializer.validated_data
        )
        return Response(CondoPaymentOutputSerializer(instance).data)

    def delete(self, request, pk: int):
        container.condo_payment_service.delete(request.user, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SetPaidStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        serializer = SetPaidStatusInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        container.condo_payment_service.mark_as_paid(
            request.user, serializer.validated_data["paid_payment_ids"]
        )
        return Response(status=status.HTTP_200_OK)
