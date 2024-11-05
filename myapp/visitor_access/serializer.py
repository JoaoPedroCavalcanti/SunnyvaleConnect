from rest_framework.serializers import ModelSerializer
from visitor_access.models import VisitorAccessModel
from rest_framework.exceptions import ValidationError
from sunnyValeConnect.utils.mixing_and_unmixing_strings import mix_strings
from sunnyValeConnect.utils.settings_config import base_url_visitor_access, secret_mixin_string
from datetime import timedelta
from django.utils import timezone
from sunnyValeConnect.utils.send_email_to_visitor import send_link_email

class VisitorAccessSerializer(ModelSerializer):
    class Meta:
        model = VisitorAccessModel
        fields = '__all__'
        read_only_fields = ['id', 'checkin_code', 'checkout_code', 'checkin_date_time', 'link_checkin', 
                            'link_checkout', 'status', 'created_at', 'updated_at'
                           ]
        
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)  
        super().__init__(*args, **kwargs)
        
    def validate(self, attrs):
        if self.user.is_staff:
            if attrs.get('host_user') == None:
                raise ValidationError({'host_user': 'This field is required for staff users.'})
            return attrs
        if attrs.get('host_user'):
            raise ValidationError({'host_user': 'This field is automatically set to the current user.'})
        attrs['host_user'] = self.user
        return attrs
    
    
    def validate_scheduled_date(self, value):
        if value < timezone.now():
            raise ValidationError({"Scheduled_date": "You can not create a visitor access with a past date."})
        return value
    
    def create(self, validated_data):
        validated_data['checkin_date_time'] = validated_data['scheduled_date']
        validated_data['status'] = 'Scheduled'
        # Primeiro, cria o objeto com os dados fornecidos
        instance = super().create(validated_data)
        # Definir o checkout_date_time, se ele for None
        if instance.checkout_date_time == None:
            instance.checkout_date_time = instance.checkin_date_time + timedelta(hours=3)
        # Gere o link_checkin após a criação do objeto (e ai posso acessar o id)
        mixed_string = mix_strings(string=str(instance.id), mix_code=secret_mixin_string)
        link_checkin = base_url_visitor_access + f'/checkin/{mixed_string}'
        
        # Atualize o objeto com o link_checkin
        instance.link_checkin = link_checkin
        
        # Seending email with link_checkin
        email = validated_data['email']
        user_name = validated_data['host_user']
        datetime_checkin = validated_data['checkin_date_time']
        visitor_name = validated_data['visitor_name']
        send_link_email(to_email=email, datetime_checkin=datetime_checkin, link_email=link_checkin, user_name=user_name, visitor_name=visitor_name)
        
        # Saving instance with changes
        instance.save()
        return instance
