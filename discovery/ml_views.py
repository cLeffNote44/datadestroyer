"""
API views for ML classification functionality.
"""

import logging

from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from .ml import HybridClassificationEngine

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
