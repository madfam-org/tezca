from django.urls import path
from .views import CalculationView
from .search_views import SearchView

urlpatterns = [
    path('calculate/', CalculationView.as_view(), name='calculate'),
    path('search/', SearchView.as_view(), name='search'),
]
