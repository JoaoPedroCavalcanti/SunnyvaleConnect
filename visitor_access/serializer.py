from rest_framework.fields import empty
from rest_framework.serializers import ModelSerializer
from visitor_access.models import VisitorAccessModel
from rest_framework.exceptions import ValidationError


class VisitorAccessSerializer(ModelSerializer):
    class Meta:
        model = VisitorAccessModel
        fields = '__all__'
        
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
