from django.shortcuts import render
from visitor_access.serializer import VisitorAccessSerializer
from rest_framework.viewsets import ModelViewSet
from visitor_access.models import VisitorAccessModel
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from django.shortcuts import get_object_or_404

class VisitorAccessViewSet(ModelViewSet):
    serializer_class = VisitorAccessSerializer
    queryset = VisitorAccessModel.objects.all()
    permission_classes = [IsAuthenticated, ]

    def get_serializer(self, *args, **kwargs):
        kwargs['user'] = self.request.user
        return super().get_serializer(*args, **kwargs)
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return VisitorAccessModel.objects.all()
        return VisitorAccessModel.objects.filter(host_user = self.request.user).order_by('-scheduled_date')

         
    def destroy(self, request, *args, **kwargs):
        obj = get_object_or_404(VisitorAccessModel, pk = kwargs['pk'])
        if obj.scheduled_date < timezone.now():
            raise ValidationError("You can not delete a past visitor access.")
        
        return super().destroy(request, *args, **kwargs)