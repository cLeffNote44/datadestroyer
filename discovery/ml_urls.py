"""
URL routes for ML classification API endpoints.
"""

from django.urls import path

from .ml_views import MLClassificationView, MLEngineStatsView, batch_classify

urlpatterns = [
    path("classify/", MLClassificationView.as_view(), name="ml-classify"),
    path("batch-classify/", batch_classify, name="ml-batch-classify"),
    path("stats/", MLEngineStatsView.as_view(), name="ml-stats"),
]
