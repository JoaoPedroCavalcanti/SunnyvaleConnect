from rest_framework.viewsets import ModelViewSet
from django.contrib.auth import get_user_model
from users.serializers import UserSerializer
from django.shortcuts import get_object_or_404

class UserViewSet(ModelViewSet):
    serializer_class = UserSerializer
    
    def get_queryset(self):
        User = get_user_model()
        # qs = get_object_or_404(User, pk = self.pk)
        qs = User.objects.all()
        return qs
    