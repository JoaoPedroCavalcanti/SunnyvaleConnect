from django.shortcuts import render
from visitor_access.serializer import VisitorAccessSerializer
from rest_framework.viewsets import ModelViewSet
from visitor_access.models import VisitorAccessModel
from visitor_access.permissions import IsAuthenticatedOrCheckInAndCheckOut
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from sunnyValeConnect.utils.mixing_and_unmixing_strings import unmix_strings
from sunnyValeConnect.utils.settings_config import secret_mixin_string
from sunnyValeConnect.utils.generate_checkin_and_checkout import generate_five_digits_code
from rest_framework.response import Response
from datetime import timedelta

class VisitorAccessViewSet(ModelViewSet):
    serializer_class = VisitorAccessSerializer
    permission_classes = [IsAuthenticatedOrCheckInAndCheckOut, ]

    def get_serializer(self, *args, **kwargs):
        kwargs['user'] = self.request.user
        return super().get_serializer(*args, **kwargs)

    def get_queryset(self):
        if self.request.user.is_staff:
            return VisitorAccessModel.objects.all().order_by('-scheduled_date')
        return VisitorAccessModel.objects.filter(host_user = self.request.user).order_by('-scheduled_date')

         
    def destroy(self, request, *args, **kwargs):
        obj = get_object_or_404(VisitorAccessModel, pk = kwargs['pk'])
        if obj.scheduled_date < timezone.now():
            raise ValidationError("You can not delete a past visitor access.")
        
        return super().destroy(request, *args, **kwargs)
    

    @action(
        methods=['get'],
        detail=False,
        url_path='checkin/(?P<visitor_access_link_checkin>[^/.]+)'
    )
    def checkin(self, request, *args, **kwargs):
        obj_id = unmix_strings(kwargs.get('visitor_access_link_checkin'), secret_mixin_string)
        obj = get_object_or_404(VisitorAccessModel, id = obj_id)
        # Check if checkin_date_time in visitor_access is > datetime.now and < checkout_date_time     
        if obj.checkin_date_time < timezone.now() and timezone.now() < obj.checkout_date_time:
            checkin_code = generate_five_digits_code()
            return Response({'checkin_code': checkin_code})
        
    @action(
        methods=['get'],
        detail=False,
        url_path='checkout/(?P<visitor_access_link_checkout>[^/.]+)'
    )
    def checkout(self, request, *args, **kwargs):
        obj_id = unmix_strings(kwargs.get('visitor_access_link_checkout'), secret_mixin_string)
        obj = get_object_or_404(VisitorAccessModel, id = obj_id)
        # Check if visitor did checkin  
        if ( obj.scheduled_date - timezone.now() ) < timedelta(hours=10):
            checkout_code = generate_five_digits_code()
            return Response({'checkout_code': checkout_code})
        