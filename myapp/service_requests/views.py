from rest_framework import status
from service_requests.models import ServiceRequestModel
from service_requests.serializer import ServiceRequestSerializer
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.exceptions import ValidationError
from rest_framework import status


@api_view(http_method_names=["GET", "POST"])
@permission_classes([IsAuthenticated])
def service_requests_list_and_create(request):
    def get_user_object_or_all_objects():
        all_objects = []
        if request.user.is_staff:
            all_objects = ServiceRequestModel.objects.all().order_by(
                "-request_scheduled_date"
            )
            return all_objects

        all_objects = ServiceRequestModel.objects.filter(
            requester_user_id=request.user
        ).order_by("-request_scheduled_date")
        return all_objects

    if request.method == "GET":
        service_requests = get_user_object_or_all_objects()
        serializer = ServiceRequestSerializer(instance=service_requests, many=True)
        return Response(serializer.data, status.HTTP_200_OK)

    elif request.method == "POST":
        serializer = ServiceRequestSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status.HTTP_201_CREATED)
        return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)


@api_view(http_method_names=["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def service_request_detail_retrieve_and_delete(request, pk):
    if request.method == "GET":
        service_request = get_object_or_404(ServiceRequestModel, pk=pk)

        # Check if user logged is admin. If not, check if requester_user_id is the same as yours
        if (
            service_request.requester_user_id != request.user.id
            and not request.user.is_staff
        ):
            return Response(
                {"detail": "No Service Request matches the given query."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ServiceRequestSerializer(instance=service_request)
        return Response(serializer.data, status.HTTP_200_OK)

    if request.method == "PATCH":
        service_request = get_object_or_404(ServiceRequestModel, pk=pk)

        # Check if user logged is admin. If not, check if requester_user_id is the same as yours
        if (
            service_request.requester_user_id != request.user.id
            and not request.user.is_staff
        ):
            return Response(
                {"detail": "No Service Request matches the given query."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ServiceRequestSerializer(
            instance=service_request, data=request.data, partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status.HTTP_200_OK)

        return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)

    if request.method == "DELETE":
        service_request = get_object_or_404(ServiceRequestModel, pk=pk)

        # Check if user logged is admin. If not, check if requester_user_id is the same as yours
        if (
            service_request.requester_user_id != request.user.id
            and not request.user.is_staff
        ):
            return Response(
                {"detail": "No Service Request matches the given query."},
                status=status.HTTP_404_NOT_FOUND,
            )

        service_request.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(http_method_names=["PATCH"])
@permission_classes([IsAdminUser])
def accept_request(request, pk, accept_or_decline):
    service_request = get_object_or_404(ServiceRequestModel, pk=pk)

    if accept_or_decline != "accept" and accept_or_decline != "decline":
        return Response(status=status.HTTP_400_BAD_REQUEST)

    if accept_or_decline == "accept":
        service_request.status = "accepted"
        serializer = ServiceRequestSerializer(
            instance=service_request, data=request.data, partial=True
        )

        if serializer.is_valid():
            serializer.save()

        else:
            return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)

    elif accept_or_decline == "decline":
        service_request.status = "declined"
        serializer = ServiceRequestSerializer(
            instance=service_request, data=request.data, partial=True
        )

        if serializer.is_valid():
            serializer.save()

        else:
            return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)

    service_request.save()

    return Response(
        {
            "Status": f"Service Request from {service_request.requester_user} was {service_request.status}",
            "Details": request.data,
        },
        status=status.HTTP_200_OK,
    )
