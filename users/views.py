from rest_framework.viewsets import ModelViewSet
from django.contrib.auth import get_user_model
from users.serializers import UserSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny
# from rest_framework.exceptions import PermissionDenied
from users.permissions import CanCreateUser

class UserViewSet(ModelViewSet):
    serializer_class = UserSerializer
    http_method_names = ['get', 'post', 'delete', 'patch']
    permission_classes = [IsAuthenticated, ]
    
    def get_queryset(self):
        User = get_user_model()
        
        if self.request.user.is_staff:
            return User.objects.all()
        
        return User.objects.filter(pk=self.request.user.pk)
    
    # def create(self, request, *args, **kwargs):
    #     if not request.user.is_staff or request.user.is_authenticated:
    #         raise PermissionDenied('You do not have permission to create a user.')
    #         AllowAny()
    #     return super().create(request, *args, **kwargs)
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [CanCreateUser()]
        return super().get_permissions()