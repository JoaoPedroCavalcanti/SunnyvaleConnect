from django.shortcuts import render
from visitor_access.serializer import VisitorAccessSerializer
from rest_framework.viewsets import ModelViewSet
from visitor_access.models import VisitorAccessModel

class VisitorAccessViewSet(ModelViewSet):
    serializer_class = VisitorAccessSerializer
    queryset = VisitorAccessModel.objects.all()
