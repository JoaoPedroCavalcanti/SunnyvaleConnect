from rest_framework.viewsets import ModelViewSet
from bbq_reservations.serializer import BBQReservationSerializer
from bbq_reservations.models import BBQReservationModel
from rest_framework.permissions import IsAuthenticated


class BBQReservationViewSet(ModelViewSet):
    serializer_class = BBQReservationSerializer
    permission_classes = [IsAuthenticated, ]
    http_method_names = ['get', 'post', 'patch', 'delete']

    # Overwriting method to pass the user to the serializer
    def get_serializer(self, *args, **kwargs):
        kwargs['user'] = self.request.user  
        return super().get_serializer(*args, **kwargs)
    
    def get_queryset(self):
        return BBQReservationModel.objects.all().order_by('-reservation_date')
    