"""
URL routes for ML classification API endpoints.
"""

from django.urls import path

from .ml_views import (
    MLClassificationView,
    MLEngineStatsView,
    MLFeedbackListView,
    MLFeedbackStatsView,
    MLFeedbackView,
    MLTrainingDataView,
    batch_classify,
)

urlpatterns = [
    # Classification endpoints
    path("classify/", MLClassificationView.as_view(), name="ml-classify"),
    path("batch-classify/", batch_classify, name="ml-batch-classify"),
    path("stats/", MLEngineStatsView.as_view(), name="ml-stats"),
    # Active Learning - Feedback endpoints
    path("feedback/", MLFeedbackView.as_view(), name="ml-feedback"),
    path("feedback/list/", MLFeedbackListView.as_view(), name="ml-feedback-list"),
    path("feedback/stats/", MLFeedbackStatsView.as_view(), name="ml-feedback-stats"),
    # Training data management
    path("training-data/", MLTrainingDataView.as_view(), name="ml-training-data"),
]
