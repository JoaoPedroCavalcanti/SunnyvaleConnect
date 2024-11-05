from rest_framework.serializers import ModelSerializer, ValidationError
from django.contrib.auth import get_user_model
from sunnyValeConnect.utils.passwordFunctions import hasUpperCase, hasAtLeast8Characters, hasSpecialCharacter

class UserSerializer(ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ['id', 'username', 'password', 'first_name', 'last_name', 'email']
        read_only_fields = ['id']
        extra_kwargs = {
            'username': {'required': True},
            'password': {'write_only': True, 'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
            'email': {'required': True},
        }

        
    def create(self, validated_data):
        User = get_user_model()
        user = User.objects.create_user(
            username = validated_data.get('username'),
            password = validated_data.get('password'),
            first_name = validated_data.get('first_name'),
            last_name = validated_data.get('last_name'),
            email = validated_data.get('email'),
        )
        return user
    
    def validate_email(self, value):
        User = get_user_model()
        if User.objects.filter(email=value):
            raise ValidationError('An account with this email address already exists.')
            
        return value
    
    def validate_password(self, value):
        errors_list = []

        if not hasUpperCase(value):
            errors_list.append("Password must contain at least one uppercase letter.")
        
        if not hasAtLeast8Characters(value):
            errors_list.append("Password must be at least 8 characters long.")
            
        if not hasSpecialCharacter(value):
            errors_list.append("Password must be have at least 1 special character(ex: !$%*<).")

        if errors_list:
            raise ValidationError(errors_list)

        return value