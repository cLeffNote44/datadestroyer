"""
URL routing for the discovery system API
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import DiscoveryDashboardView, GovernanceDashboardView

# Create a router for ViewSets (will add more when we complete the ViewSets)
router = DefaultRouter()

# Individual API views
urlpatterns = [
    # Dashboard endpoints
    path('dashboard/', DiscoveryDashboardView.as_view(), name='discovery-dashboard'),
    path('governance-dashboard/', GovernanceDashboardView.as_view(), name='governance-dashboard'),

    # ML Classification endpoints
    path('ml/', include('discovery.ml_urls')),

    # Include router URLs when ViewSets are created
    path('', include(router.urls)),
]

app_name = 'discovery'
