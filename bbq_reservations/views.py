from rest_framework.viewsets import ModelViewSet
from bbq_reservations.serializer import BBQReservationSerializer
from bbq_reservations.models import BBQReservationModel
from rest_framework.permissions import IsAuthenticated


class BBQReservationViewSet(ModelViewSet):
    serializer_class = BBQReservationSerializer
    queryset = BBQReservationModel.objects.all()
    permission_classes = [IsAuthenticated, ]
    http_method_names = ['get', 'post', 'patch', 'delete']

    # Overwriting method to pass the user to the serializer
    def get_serializer(self, *args, **kwargs):
        kwargs['user'] = self.request.user  # Passa o usuário para o serializer
        return super().get_serializer(*args, **kwargs)
    

    # def perform_create(self, serializer):
    #     if self.request.user.is_staff:
    #         return super().perform_create(serializer)
    #     serializer.save(reservation_user=self.request.user)

        