"""
URL routing for content moderation API endpoints.

Provides RESTful API endpoints for:
- Content scanning and analysis
- Policy violation management
- Moderation actions and workflows
- Pattern management and testing
- Dashboard and analytics integration
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminBulkReviewAPIView,
    AdminDashboardAPIView,
    AdminReviewActionAPIView,
    AdminReviewQueueAPIView,
    BulkScanAPIView,
    ContentScanAPIView,
    ContentScanViewSet,
    ModerationActionViewSet,
    ModerationDashboardAPIView,
    ModerationSettingsViewSet,
    PolicyViolationViewSet,
    QuarantineAPIView,
    SensitiveContentPatternViewSet,
)

# Create a router for ViewSets
router = DefaultRouter()
router.register(r"patterns", SensitiveContentPatternViewSet, basename="patterns")
router.register(r"scans", ContentScanViewSet, basename="scans")
router.register(r"violations", PolicyViolationViewSet, basename="violations")
router.register(r"actions", ModerationActionViewSet, basename="actions")
router.register(r"settings", ModerationSettingsViewSet, basename="settings")

# URL patterns
urlpatterns = [
    # API Views (non-ViewSet endpoints)
    path("scan/", ContentScanAPIView.as_view(), name="content_scan"),
    path("bulk-scan/", BulkScanAPIView.as_view(), name="bulk_scan"),
    path("quarantine/", QuarantineAPIView.as_view(), name="quarantine"),
    path("dashboard/", ModerationDashboardAPIView.as_view(), name="dashboard"),
    # Admin API endpoints
    path("admin/review-queue/", AdminReviewQueueAPIView.as_view(), name="admin_review_queue"),
    path("admin/review-action/", AdminReviewActionAPIView.as_view(), name="admin_review_action"),
    path("admin/bulk-review/", AdminBulkReviewAPIView.as_view(), name="admin_bulk_review"),
    path("admin/dashboard/", AdminDashboardAPIView.as_view(), name="admin_dashboard"),
    # Include ViewSet routes
    path("", include(router.urls)),
]

app_name = "moderation"
