from django.contrib import admin
from visitor_access.models import VisitorAccessModel

class VisitorAccessAdmin(admin.ModelAdmin):
    ...
    
admin.site.register(VisitorAccessModel)