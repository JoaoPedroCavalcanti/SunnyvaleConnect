"""Plain APIViews for visitor access."""

from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from shared.container import container
from visitor_access.serializers import (
    VisitorAccessInputSerializer,
    VisitorAccessOutputSerializer,
)


class VisitorAccessListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = container.visitor_access_service.list_for(request.user)
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = VisitorAccessOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

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


class VisitorAccessDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk: int):
        instance = container.visitor_access_service.get_for(request.user, pk)
        return Response(VisitorAccessOutputSerializer(instance).data)

    def delete(self, request, pk: int):
        container.visitor_access_service.delete(request.user, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class VisitorAccessCheckinView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, visitor_access_link_checkin: str):
        result = container.visitor_access_service.checkin(visitor_access_link_checkin)
        return Response(result)


class VisitorAccessCheckoutView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, visitor_access_link_checkout: str):
        result = container.visitor_access_service.checkout(
            visitor_access_link_checkout
        )
        return Response(result)
