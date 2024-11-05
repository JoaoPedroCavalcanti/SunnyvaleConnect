from django.urls import path
from delivery_notification import views

app_name = 'delivery_notification'

urlpatterns = [
    path(
        '',
        views.send_notification,
        name='send_delivery_notification'
    ),
    path(
        'list/',
        views.list_notifications,
        name='list_notifications'
    ),
    path(
        '<int:pk>/',
        views.detail_notification,
        name='detail_notification'
    ),
]
