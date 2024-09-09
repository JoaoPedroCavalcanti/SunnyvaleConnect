from django.urls import path
from service_requests import views

app_name = 'service_requests'

urlpatterns = [
    path(
        '',
        views.service_requests_list_and_create,
        name='service_requests_list_and_create'
    ),
    path(
        '<int:pk>/',
        views.service_request_detail_retrieve_and_delete,
        name='service_request_detail_retrieve_and_delete'
    ),
    path(
        'accept_or_decline/<int:pk>/<str:accept_or_decline>/',
        views.accept_request,
        name='accept_request'
    )
]
