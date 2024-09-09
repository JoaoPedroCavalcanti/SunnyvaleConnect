from django.contrib import admin
from service_requests.models import ServiceRequestModel

class ServiceRequestAdmin(admin.ModelAdmin):
    ...
    
admin.site.register(ServiceRequestModel)