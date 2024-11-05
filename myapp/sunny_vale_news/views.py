from django.shortcuts import render
from sunny_vale_news.serializer import SunnyValeNewsSerializer
from sunny_vale_news.models import SunnyValeNewsModel
from rest_framework.viewsets import ModelViewSet
from sunny_vale_news.permissions import IsAdminOrReadOnlyIfLogged
# Create your views here.

class SunnyValeNewsViewSet(ModelViewSet):
    serializer_class = SunnyValeNewsSerializer
    queryset = SunnyValeNewsModel.objects.all().order_by('-created_at')
    permission_classes = [IsAdminOrReadOnlyIfLogged]