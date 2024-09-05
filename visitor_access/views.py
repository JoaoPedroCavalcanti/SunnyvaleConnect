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
from sunnyValeConnect.utils.send_email_to_visitor import send_checkin_notification, send_checkout_notification


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
        if obj.status != 'Scheduled':
            
            if obj.status == 'Checked-out':
                raise ValidationError(f'You already {obj.status}')
            
        if obj.checkin_date_time < timezone.now() and timezone.now() < obj.checkout_date_time:
            
            if obj.checkin_code != '':
                return Response({'checkin_code': obj.checkin_code})
            
            checkin_code = generate_five_digits_code()
            obj.checkin_code = checkin_code
            obj.status = 'Checked-in'
            obj.save()
            
            # Send notification checkin
            user_email = obj.email
            user_name = obj.host_user
            visitor_name = obj.visitor_name
            send_checkin_notification(to_email=user_email, user_name=user_name, visitor_name=visitor_name)

            return Response({'checkin_code': checkin_code})
        
        return Response("Please checkin just in your scheduled time") 

        
    @action(
        methods=['get'],
        detail=False,
        url_path='checkout/(?P<visitor_access_link_checkout>[^/.]+)'
    )
    def checkout(self, request, *args, **kwargs):
        obj_id = unmix_strings(kwargs.get('visitor_access_link_checkout'), secret_mixin_string)
        obj = get_object_or_404(VisitorAccessModel, id = obj_id)
        
        if obj.status != 'Checked-in':
            
            if obj.status == 'Scheduled':
                raise ValidationError('You can not check-out because you did not checked-in')
        

        if ( obj.scheduled_date - timezone.now() ) < timedelta(hours=10):
            
            if obj.checkout_code != '':
                return Response({'checkout_code': obj.checkout_code})
            
            checkout_code = generate_five_digits_code()
            obj.checkout_code = checkout_code
            obj.status = 'Checked-out'
            obj.save()
            
            user_email = obj.email
            user_name = obj.host_user
            visitor_name = obj.visitor_name
            send_checkout_notification(to_email=user_email, user_name=user_name, visitor_name=visitor_name)
            
            return Response({'checkout_code': checkout_code})
    
    