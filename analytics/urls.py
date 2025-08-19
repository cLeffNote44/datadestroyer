from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AnalyticsDashboardViewSet,
    AnalyticsSnapshotViewSet,
    DataUsageMetricViewSet,
    PrivacyInsightViewSet,
    RetentionTimelineViewSet,
)

# Create a router for the analytics API
router = DefaultRouter()
router.register(r"snapshots", AnalyticsSnapshotViewSet, basename="analytics-snapshots")
router.register(r"metrics", DataUsageMetricViewSet, basename="usage-metrics")
router.register(r"insights", PrivacyInsightViewSet, basename="privacy-insights")
router.register(r"retention", RetentionTimelineViewSet, basename="retention-timeline")
router.register(r"dashboard", AnalyticsDashboardViewSet, basename="analytics-dashboard")

urlpatterns = [
    path("", include(router.urls)),
]
