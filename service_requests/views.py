from rest_framework import status
from service_requests.models import ServiceRequestModel
from service_requests.serializer import ServiceRequestSerializer
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.shortcuts import get_object_or_404


@api_view(http_method_names=['GET', 'POST'])
# @permission_classes([IsAuthenticated])
def service_requests_list_and_create(request):
    
    if request.method == 'GET':
        service_requests = ServiceRequestModel.objects.all()
        serializer = ServiceRequestSerializer(instance = service_requests, many = True)
        return Response(serializer.data, status.HTTP_200_OK)
    
    elif request.method == 'POST':
        serializer = ServiceRequestSerializer(data = request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status.HTTP_201_CREATED)
        return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)
            


@api_view(http_method_names=['GET', 'PATCH'])
def service_request_detail_retrieve_and_delete(request, pk):

    if request.method == 'GET':
        service_request = get_object_or_404(ServiceRequestModel, pk = pk)
        serializer = ServiceRequestSerializer(instance = service_request)
        return Response(serializer.data, status.HTTP_200_OK)
    
    if request.method == 'PATCH':
        service_request = get_object_or_404(ServiceRequestModel, pk = pk)
        serializer = ServiceRequestSerializer(instance = service_request, data = request.data, partial = True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status.HTTP_200_OK)
        
        return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)