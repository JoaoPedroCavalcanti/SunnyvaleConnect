from django.shortcuts import render
from hall_reservations.serializer import HallReservationSerializer
from rest_framework.viewsets import ModelViewSet
from hall_reservations.models import HallReservationModel
from rest_framework.permissions import IsAuthenticated

class HallReservationViewSet(ModelViewSet):
    serializer_class = HallReservationSerializer
    queryset = HallReservationModel.objects.all()
    permission_classes = [IsAuthenticated, ]
    
    # Send user to serializer
    def get_serializer(self, *args, **kwargs):
        kwargs['user'] = self.request.user  
        return super().get_serializer(*args, **kwargs)
    