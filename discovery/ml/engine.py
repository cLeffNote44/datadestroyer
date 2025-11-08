"""
Hybrid classification engine combining regex and ML approaches.

This is the main entry point for ML-powered classification.
"""

import logging
import time
from typing import List, Optional

from .entities import ClassificationResult, ConfidenceConfig
from .merger import ResultMerger
from .ml_classifier import MLClassifier
from .regex_classifier import RegexClassifier

logger = logging.getLogger(__name__)


class HybridClassificationEngine:
    """
    Main classification engine combining regex and ML approaches.

    Uses both regex patterns (high precision) and ML models (high recall)
    to achieve optimal classification accuracy.

    Example:
        >>> engine = HybridClassificationEngine()
        >>> result = engine.classify(
        ...     "John Smith's SSN is 123-45-6789",
        ...     classification_types=["PII"]
        ... )
        >>> print(result.entities)
        [Entity(text='John Smith', label='PII', confidence=0.95),
         Entity(text='123-45-6789', label='PII', confidence=0.99)]
    """

    def __init__(
        self,
        use_ml: bool = True,
        use_regex: bool = True,
        confidence_config: Optional[ConfidenceConfig] = None,
    ):
        """
        Initialize hybrid classification engine.

        Args:
            use_ml: Whether to use ML classification
            use_regex: Whether to use regex classification
            confidence_config: Configuration for confidence scoring
        """
        self.use_ml = use_ml
        self.use_regex = use_regex
        self.confidence_config = confidence_config or ConfidenceConfig()

        # Initialize classifiers
        self.regex_classifier = RegexClassifier() if use_regex else None
        self.ml_classifier = MLClassifier() if use_ml else None
        self.merger = ResultMerger(self.confidence_config)

        logger.info(
            f"Hybrid engine initialized (ML: {use_ml}, Regex: {use_regex})"
        )

    def classify(
        self,
        text: str,
        classification_types: Optional[List[str]] = None,
    ) -> ClassificationResult:
        """
        Classify text using hybrid approach.

        Args:
            text: Text to classify
            classification_types: Types to look for (PII, PHI, Financial, etc.)
                                If None, checks all types.

        Returns:
            ClassificationResult with detected entities

        Example:
            >>> result = engine.classify("Contact John at john@example.com")
            >>> for entity in result.entities:
            ...     print(f"{entity.text} ({entity.label}): {entity.confidence:.2f}")
            John (PII): 0.87
            john@example.com (PII): 0.98
        """
        start_time = time.time()

        # Default to all types if not specified
        if classification_types is None:
            classification_types = ["PII", "PHI", "Financial", "IP", "Confidential"]

        regex_entities = []
        ml_entities = []

        # Run regex classification
        if self.use_regex and self.regex_classifier:
            try:
                regex_entities = self.regex_classifier.classify(text, classification_types)
                logger.debug(f"Regex found {len(regex_entities)} entities")
            except Exception as e:
                logger.error(f"Regex classification error: {e}")

        # Run ML classification
        if self.use_ml and self.ml_classifier:
            try:
                ml_entities = self.ml_classifier.classify(text, classification_types)
                logger.debug(f"ML found {len(ml_entities)} entities")
            except Exception as e:
                logger.error(f"ML classification error: {e}")

        # Merge results
        merged_entities = self.merger.merge(regex_entities, ml_entities)

        # Calculate overall confidence
        overall_confidence = self.merger.calculate_overall_confidence(merged_entities)

        # Calculate processing time
        processing_time_ms = (time.time() - start_time) * 1000

        result = ClassificationResult(
            text=text,
            entities=merged_entities,
            classification_types=classification_types,
            regex_entities=regex_entities,
            ml_entities=ml_entities,
            overall_confidence=overall_confidence,
            processing_time_ms=processing_time_ms,
            metadata={
                "regex_count": len(regex_entities),
                "ml_count": len(ml_entities),
                "merged_count": len(merged_entities),
                "use_ml": self.use_ml,
                "use_regex": self.use_regex,
            },
        )

        logger.info(
            f"Classification complete: {len(merged_entities)} entities "
            f"(confidence: {overall_confidence:.2f}, time: {processing_time_ms:.0f}ms)"
        )

        return result

    def classify_batch(
        self,
        texts: List[str],
        classification_types: Optional[List[str]] = None,
    ) -> List[ClassificationResult]:
        """
        Classify multiple texts.

        Args:
            texts: List of texts to classify
            classification_types: Types to look for

        Returns:
            List of ClassificationResults
        """
        results = []
        for text in texts:
            result = self.classify(text, classification_types)
            results.append(result)
        return results

    def get_statistics(self) -> dict:
        """
        Get engine statistics.

        Returns:
            Dictionary with engine stats
        """
        stats = {
            "use_ml": self.use_ml,
            "use_regex": self.use_regex,
            "ml_loaded": self.ml_classifier._models_loaded if self.ml_classifier else False,
            "regex_patterns": len(self.regex_classifier.patterns) if self.regex_classifier else 0,
            "confidence_config": {
                "regex_base": self.confidence_config.regex_base,
                "ml_base": self.confidence_config.ml_base,
                "agreement_boost": self.confidence_config.agreement_boost,
                "high_threshold": self.confidence_config.high_threshold,
                "minimum_threshold": self.confidence_config.minimum_threshold,
            },
        }
        return stats
