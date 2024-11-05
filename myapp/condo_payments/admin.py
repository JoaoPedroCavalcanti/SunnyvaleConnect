from django.contrib import admin
from condo_payments.models import CondoPaymentModel

class CondoPaymentAdmin(admin.ModelAdmin):
    ...
    
admin.site.register(CondoPaymentModel)