from django.urls import path

from condominiums.views import CondominiumListCreateView, CondominiumLookupView

app_name = "condominiums"

urlpatterns = [
    path("lookup/", CondominiumLookupView.as_view(), name="lookup"),
    path("", CondominiumListCreateView.as_view(), name="list-create"),
]
