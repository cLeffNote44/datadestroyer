"""
API views for ML classification functionality.
"""

import logging
from typing import Dict, List

from django.db.models import Avg, Count, Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from .ml import HybridClassificationEngine
from .ml_models import (
    ClassificationFeedback,
    MLClassificationResult,
    MLModel,
    TrainingDataset,
)

logger = logging.getLogger(__name__)


class MLClassificationView(APIView):
    """
    ML-powered classification endpoint.

    Classifies text using hybrid regex + ML approach.
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "classification_types": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "use_ml": {"type": "boolean"},
                    "use_regex": {"type": "boolean"},
                },
                "required": ["text"],
            }
        },
        responses={200: dict},
    )
    def post(self, request):
        """
        Classify text using ML.

        Request body:
            {
                "text": "Text to classify",
                "classification_types": ["PII", "PHI"],  // optional
                "use_ml": true,  // optional, default true
                "use_regex": true  // optional, default true
            }

        Response:
            {
                "entities": [
                    {
                        "text": "John Smith",
                        "start": 0,
                        "end": 10,
                        "label": "PII",
                        "sublabel": "PERSON",
                        "confidence": 0.95,
                        "source": "spacy_ner",
                        "metadata": {}
                    }
                ],
                "overall_confidence": 0.92,
                "processing_time_ms": 145,
                "entity_count": 3,
                "regex_entity_count": 2,
                "ml_entity_count": 2
            }
        """
        # Validate request
        text = request.data.get("text")
        if not text:
            return Response(
                {"error": "Text is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        classification_types = request.data.get("classification_types")
        use_ml = request.data.get("use_ml", True)
        use_regex = request.data.get("use_regex", True)

        try:
            # Initialize engine
            engine = HybridClassificationEngine(
                use_ml=use_ml,
                use_regex=use_regex,
            )

            # Classify
            result = engine.classify(text, classification_types)

            # Return result
            return Response(result.to_dict())

        except Exception as e:
            logger.error(f"ML classification error: {e}", exc_info=True)
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class MLEngineStatsView(APIView):
    """Get ML engine statistics"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """
        Get ML engine statistics.

        Response:
            {
                "use_ml": true,
                "use_regex": true,
                "ml_loaded": true,
                "regex_patterns": 8,
                "confidence_config": {...}
            }
        """
        try:
            engine = HybridClassificationEngine()
            stats = engine.get_statistics()
            return Response(stats)
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def batch_classify(request):
    """
    Classify multiple texts at once.

    Request body:
        {
            "texts": ["text1", "text2", "text3"],
            "classification_types": ["PII"]  // optional
        }

    Response:
        {
            "results": [
                {...},  // ClassificationResult for text1
                {...},  // ClassificationResult for text2
                {...}   // ClassificationResult for text3
            ],
            "total_count": 3,
            "total_entities": 15
        }
    """
    texts = request.data.get("texts", [])
    if not texts:
        return Response(
            {"error": "texts array is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    classification_types = request.data.get("classification_types")

    try:
        engine = HybridClassificationEngine()
        results = engine.classify_batch(texts, classification_types)

        response_data = {
            "results": [r.to_dict() for r in results],
            "total_count": len(results),
            "total_entities": sum(r.entity_count for r in results),
        }

        return Response(response_data)

    except Exception as e:
        logger.error(f"Batch classification error: {e}", exc_info=True)
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class MLFeedbackView(APIView):
    """
    Submit feedback on ML classification results.

    This is the core of the active learning system - user corrections
    are collected and used to improve the models over time.
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Original classified text"},
                    "entities": {
                        "type": "array",
                        "description": "Detected entities",
                        "items": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string"},
                                "start": {"type": "integer"},
                                "end": {"type": "integer"},
                                "label": {"type": "string"},
                                "sublabel": {"type": "string"},
                            },
                        },
                    },
                    "is_correct": {"type": "boolean", "description": "Is the classification correct?"},
                    "corrected_entities": {
                        "type": "array",
                        "description": "User's corrected entities (if is_correct=false)",
                        "items": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string"},
                                "start": {"type": "integer"},
                                "end": {"type": "integer"},
                                "label": {"type": "string"},
                                "sublabel": {"type": "string"},
                            },
                        },
                    },
                    "notes": {"type": "string", "description": "Optional feedback notes"},
                },
                "required": ["text", "entities", "is_correct"],
            }
        },
        responses={201: dict},
    )
    def post(self, request):
        """
        Submit classification feedback.

        Request body:
            {
                "text": "John Smith's SSN is 123-45-6789",
                "entities": [
                    {
                        "text": "John Smith",
                        "start": 0,
                        "end": 10,
                        "label": "PII",
                        "sublabel": "PERSON"
                    }
                ],
                "is_correct": false,
                "corrected_entities": [
                    {
                        "text": "John Smith",
                        "start": 0,
                        "end": 10,
                        "label": "PII",
                        "sublabel": "PERSON"
                    },
                    {
                        "text": "123-45-6789",
                        "start": 22,
                        "end": 33,
                        "label": "PII",
                        "sublabel": "SSN"
                    }
                ],
                "notes": "Missed the SSN"
            }

        Response:
            {
                "id": "uuid",
                "status": "created",
                "message": "Feedback recorded successfully",
                "will_be_used_for_training": true
            }
        """
        # Validate request
        text = request.data.get("text")
        entities = request.data.get("entities", [])
        is_correct = request.data.get("is_correct")

        if not text:
            return Response(
                {"error": "text is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if is_correct is None:
            return Response(
                {"error": "is_correct is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Store the classification result first
            ml_result = MLClassificationResult.objects.create(
                text=text,
                detected_entities=entities,
                entity_count=len(entities),
                confidence_score=request.data.get("confidence", 0.0),
                classified_by=request.user,
            )

            # Create feedback
            corrected_entities = request.data.get("corrected_entities")
            feedback = ClassificationFeedback.objects.create(
                result=ml_result,
                user=request.user,
                is_correct=is_correct,
                corrected_entities=corrected_entities or [],
                feedback_notes=request.data.get("notes", ""),
            )

            # If incorrect, create training data
            if not is_correct and corrected_entities:
                TrainingDataset.objects.create(
                    text=text,
                    entities=corrected_entities,
                    source="user_feedback",
                    classification_type=corrected_entities[0].get("label", "PII") if corrected_entities else "PII",
                    created_by=request.user,
                    verified=False,  # Requires verification before training
                )

            logger.info(
                f"Feedback recorded: user={request.user.id}, "
                f"is_correct={is_correct}, entities={len(entities)}"
            )

            return Response(
                {
                    "id": str(feedback.id),
                    "status": "created",
                    "message": "Feedback recorded successfully",
                    "will_be_used_for_training": not is_correct,
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            logger.error(f"Error recording feedback: {e}", exc_info=True)
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class MLFeedbackListView(APIView):
    """
    List and filter classification feedback.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """
        Get feedback list with optional filters.

        Query parameters:
            - is_correct: true/false
            - incorporated: true/false (already used for training)
            - limit: number of results (default 50)
            - offset: pagination offset (default 0)
            - user_id: filter by user

        Response:
            {
                "count": 150,
                "results": [
                    {
                        "id": "uuid",
                        "text": "...",
                        "is_correct": false,
                        "corrected_entities": [...],
                        "created_at": "2025-11-08T12:00:00Z",
                        "incorporated_in_training": false
                    }
                ]
            }
        """
        # Build query
        queryset = ClassificationFeedback.objects.all().select_related("result", "user")

        # Apply filters
        if "is_correct" in request.query_params:
            is_correct = request.query_params["is_correct"].lower() == "true"
            queryset = queryset.filter(is_correct=is_correct)

        if "incorporated" in request.query_params:
            incorporated = request.query_params["incorporated"].lower() == "true"
            queryset = queryset.filter(incorporated_in_training=incorporated)

        if "user_id" in request.query_params:
            queryset = queryset.filter(user_id=request.query_params["user_id"])

        # Pagination
        limit = int(request.query_params.get("limit", 50))
        offset = int(request.query_params.get("offset", 0))

        total_count = queryset.count()
        feedback_items = queryset.order_by("-created_at")[offset : offset + limit]

        # Serialize results
        results = [
            {
                "id": str(fb.id),
                "text": fb.result.text,
                "is_correct": fb.is_correct,
                "corrected_entities": fb.corrected_entities,
                "feedback_notes": fb.feedback_notes,
                "created_at": fb.created_at.isoformat(),
                "incorporated_in_training": fb.incorporated_in_training,
                "user": {
                    "id": fb.user.id,
                    "username": fb.user.username if hasattr(fb.user, "username") else str(fb.user),
                },
            }
            for fb in feedback_items
        ]

        return Response(
            {
                "count": total_count,
                "limit": limit,
                "offset": offset,
                "results": results,
            }
        )


class MLFeedbackStatsView(APIView):
    """
    Get feedback statistics for monitoring and reporting.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """
        Get feedback statistics.

        Response:
            {
                "total_feedback": 500,
                "correct_classifications": 450,
                "incorrect_classifications": 50,
                "accuracy_rate": 0.90,
                "pending_training_samples": 30,
                "incorporated_samples": 20,
                "feedback_by_day": [...]
            }
        """
        # Overall stats
        total = ClassificationFeedback.objects.count()
        correct = ClassificationFeedback.objects.filter(is_correct=True).count()
        incorrect = total - correct

        # Training data stats
        pending_training = ClassificationFeedback.objects.filter(
            is_correct=False, incorporated_in_training=False
        ).count()

        incorporated = ClassificationFeedback.objects.filter(
            incorporated_in_training=True
        ).count()

        # Calculate accuracy
        accuracy_rate = correct / total if total > 0 else 0.0

        # Feedback over time (last 30 days)
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
        recent_feedback = (
            ClassificationFeedback.objects.filter(created_at__gte=thirty_days_ago)
            .values("created_at__date")
            .annotate(
                count=Count("id"),
                correct_count=Count("id", filter=Q(is_correct=True)),
            )
            .order_by("created_at__date")
        )

        feedback_by_day = [
            {
                "date": item["created_at__date"].isoformat(),
                "total": item["count"],
                "correct": item["correct_count"],
                "incorrect": item["count"] - item["correct_count"],
            }
            for item in recent_feedback
        ]

        # Top users providing feedback
        top_users = (
            ClassificationFeedback.objects.values("user__id", "user__username")
            .annotate(feedback_count=Count("id"))
            .order_by("-feedback_count")[:10]
        )

        return Response(
            {
                "total_feedback": total,
                "correct_classifications": correct,
                "incorrect_classifications": incorrect,
                "accuracy_rate": round(accuracy_rate, 4),
                "pending_training_samples": pending_training,
                "incorporated_samples": incorporated,
                "feedback_by_day": feedback_by_day,
                "top_contributors": [
                    {
                        "user_id": user["user__id"],
                        "username": user["user__username"],
                        "feedback_count": user["feedback_count"],
                    }
                    for user in top_users
                ],
            }
        )


class MLTrainingDataView(APIView):
    """
    Manage training datasets.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """
        List training datasets.

        Query parameters:
            - verified: true/false
            - classification_type: PII, PHI, etc.
            - source: user_feedback, manual, imported
            - limit: number of results (default 50)
            - offset: pagination offset (default 0)

        Response:
            {
                "count": 100,
                "results": [...]
            }
        """
        queryset = TrainingDataset.objects.all()

        # Apply filters
        if "verified" in request.query_params:
            verified = request.query_params["verified"].lower() == "true"
            queryset = queryset.filter(verified=verified)

        if "classification_type" in request.query_params:
            queryset = queryset.filter(
                classification_type=request.query_params["classification_type"]
            )

        if "source" in request.query_params:
            queryset = queryset.filter(source=request.query_params["source"])

        # Pagination
        limit = int(request.query_params.get("limit", 50))
        offset = int(request.query_params.get("offset", 0))

        total_count = queryset.count()
        datasets = queryset.order_by("-created_at")[offset : offset + limit]

        results = [
            {
                "id": str(ds.id),
                "text": ds.text,
                "entities": ds.entities,
                "classification_type": ds.classification_type,
                "source": ds.source,
                "verified": ds.verified,
                "language": ds.language,
                "created_at": ds.created_at.isoformat(),
                "usage_count": ds.usage_count,
            }
            for ds in datasets
        ]

        return Response(
            {
                "count": total_count,
                "limit": limit,
                "offset": offset,
                "results": results,
            }
        )

    def post(self, request):
        """
        Add training data manually.

        Request body:
            {
                "text": "Sample text",
                "entities": [
                    {
                        "text": "John",
                        "start": 0,
                        "end": 4,
                        "label": "PII",
                        "sublabel": "PERSON"
                    }
                ],
                "classification_type": "PII",
                "verified": false
            }

        Response:
            {
                "id": "uuid",
                "status": "created"
            }
        """
        text = request.data.get("text")
        entities = request.data.get("entities", [])
        classification_type = request.data.get("classification_type", "PII")

        if not text or not entities:
            return Response(
                {"error": "text and entities are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            dataset = TrainingDataset.objects.create(
                text=text,
                entities=entities,
                classification_type=classification_type,
                source="manual",
                created_by=request.user,
                verified=request.data.get("verified", False),
            )

            return Response(
                {
                    "id": str(dataset.id),
                    "status": "created",
                    "message": "Training data added successfully",
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            logger.error(f"Error adding training data: {e}", exc_info=True)
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
