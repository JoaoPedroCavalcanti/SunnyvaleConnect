from django.contrib import admin
from hall_reservations.models import HallReservationModel


class HallReservationAdmin(admin.ModelAdmin): ...


admin.site.register(HallReservationModel)
