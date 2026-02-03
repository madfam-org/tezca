from django.urls import path
from .views import CalculationView, IngestionView
from .search_views import SearchView
from .law_views import LawDetailView, LawListView, law_articles, states_list, law_stats

urlpatterns = [
    path('calculate/', CalculationView.as_view(), name='calculate'),
    path('search/', SearchView.as_view(), name='search'),
    path('ingest/', IngestionView.as_view(), name='ingest'),
    path('stats/', law_stats, name='law-stats'),
    path('laws/', LawListView.as_view(), name='law-list'),
    path('laws/<str:law_id>/', LawDetailView.as_view(), name='law-detail'),
    path('laws/<str:law_id>/articles/', law_articles, name='law-articles'),
    path('states/', states_list, name='states-list'),
]
