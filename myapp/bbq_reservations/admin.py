from django.contrib import admin
from bbq_reservations.models import BBQReservationModel


class BBQReservationAdmin(admin.ModelAdmin): ...


admin.site.register(BBQReservationModel)
