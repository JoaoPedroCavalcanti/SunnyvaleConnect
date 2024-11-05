from hall_reservations.models import HallReservationModel
from rest_framework.serializers import ModelSerializer
from rest_framework.exceptions import ValidationError
from datetime import date, timedelta

class HallReservationSerializer(ModelSerializer):    
    class Meta:
        model = HallReservationModel
        fields = ['id', 'reservation_user', 'reservation_date', 'guest_count']
        read_only_fields = ['id']
        extra_kwargs = {
            'reservation_user': {'required': False},
            'reservation_date': {'required': True},
            'guest_count': {'required': False},
            }
        
    # Recieve the user from the view
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)  
        super().__init__(*args, **kwargs)
    
    # If no admin, the reservation_user can not me pased and will fill the reservation_user with the user.
    # If is admin, the reservation_user need to be passed.
    def validate(self, attrs):
        if not self.user.is_staff:
            if attrs.get('reservation_user'):
                raise ValidationError('You can not pass a reservation_user.')
            
            attrs['reservation_user'] = self.user
            return super().validate(attrs)
        
        if not attrs.get('reservation_user'):
            raise ValidationError('reservation_user can not be empty.')
        return super().validate(attrs)
        
    def validate_reservation_date(self, value):
        # Can't book in a day in the past
        if value < date.today():
            raise ValidationError('You can not book in a past day.')
        
        # Can't book in a day already booked
        if HallReservationModel.objects.filter(reservation_date = value):
            raise ValidationError('The Hall has already been booked.')
    
        # Can't book if user is not admin and the date is less than 30 days from the last book'
        if self.user.is_staff:
            return value
        users_books = HallReservationModel.objects.filter(reservation_user = self.user)
        # Get the last book from an user
        last_book = date(2000, 1, 1)
        for book in users_books:
            if book.reservation_date > last_book:
                last_book = book.reservation_date
        
        # Compare this last bookment with the day the user is trying to book.
        if value - last_book < timedelta(days=30):
            raise ValidationError('You can not book the hall with less than 30 days before your last bookment.')
        
        return value