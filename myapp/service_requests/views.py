"""Plain APIViews for service requests."""

from rest_framework import status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from service_requests.serializers import (
    ServiceRequestInputSerializer,
    ServiceRequestOutputSerializer,
    ServiceRequestPatchSerializer,
)
from shared.container import container


class ServiceRequestListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = container.service_request_service.list_for(request.user)
        serializer = ServiceRequestOutputSerializer(items, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ServiceRequestInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        instance = container.service_request_service.create(serializer.validated_data)
        return Response(
            ServiceRequestOutputSerializer(instance).data,
            status=status.HTTP_201_CREATED,
        )


class ServiceRequestDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk: int):
        instance = container.service_request_service.get_for(request.user, pk)
        return Response(ServiceRequestOutputSerializer(instance).data)

    def patch(self, request, pk: int):
        serializer = ServiceRequestPatchSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        instance = container.service_request_service.update(
            request.user, pk, serializer.validated_data
        )
        return Response(ServiceRequestOutputSerializer(instance).data)

    def delete(self, request, pk: int):
        container.service_request_service.delete(request.user, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AcceptOrDeclineServiceRequestView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, pk: int, accept_or_decline: str):
        instance = container.service_request_service.set_status(
            pk, accept_or_decline, request.data
        )
        return Response(
            {
                "Status": f"Service Request from {instance.requester_user} was {instance.status}",
                "Details": request.data,
            },
            status=status.HTTP_200_OK,
        )
