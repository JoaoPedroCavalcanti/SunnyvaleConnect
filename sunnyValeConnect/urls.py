from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

urlpatterns = [
    path('admin/', 
         admin.site.urls
        ),
    
    path('user/', 
         include('users.urls')
        ),
    
    path('bbq/', 
         include('bbq_reservations.urls')
        ),
    
    path('hall/', 
         include('hall_reservations.urls')
        ),
    
    path('visitor_access/', 
         include('visitor_access.urls')
        ),
    
    path('api/token/', 
           TokenObtainPairView.as_view(), 
           name='token_obtain_pair'
      ),
    
    path('api/token/refresh/', 
           TokenRefreshView.as_view(), 
           name='token_refresh'
        ),
      
    path('api/token/verify/', 
           TokenVerifyView.as_view(), 
           name='token_verify'
        ),
    
]
