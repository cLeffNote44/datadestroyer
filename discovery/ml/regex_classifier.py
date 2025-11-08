"""
Regex-based classifier wrapper.

Wraps existing regex patterns from moderation system for use in hybrid classification.
"""

import logging
import re
from typing import List, Optional

from .entities import Entity, EntitySource

logger = logging.getLogger(__name__)


# Common regex patterns for sensitive data
# These mirror the patterns from moderation.models.SensitiveContentPattern
REGEX_PATTERNS = {
    "SSN": {
        "pattern": r"\b\d{3}-\d{2}-\d{4}\b",
        "label": "PII",
        "sublabel": "SSN",
        "confidence": 0.99,
    },
    "CREDIT_CARD": {
        "pattern": r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
        "label": "Financial",
        "sublabel": "CREDIT_CARD",
        "confidence": 0.95,
    },
    "EMAIL": {
        "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "label": "PII",
        "sublabel": "EMAIL",
        "confidence": 0.98,
    },
    "PHONE": {
        "pattern": r"\b\(?\d{3}\)?[- ]?\d{3}[- ]?\d{4}\b",
        "label": "PII",
        "sublabel": "PHONE",
        "confidence": 0.95,
    },
    "IP_ADDRESS": {
        "pattern": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        "label": "PII",
        "sublabel": "IP_ADDRESS",
        "confidence": 0.90,
    },
    "MEDICAL_ID": {
        "pattern": r"\b(MRN|PATIENT|MED)[- ]?\d{5,10}\b",
        "label": "PHI",
        "sublabel": "MEDICAL_ID",
        "confidence": 0.92,
    },
    "DATE_OF_BIRTH": {
        "pattern": r"\b(DOB|Date of Birth):\s*\d{1,2}/\d{1,2}/\d{4}\b",
        "label": "PII",
        "sublabel": "DATE_OF_BIRTH",
        "confidence": 0.95,
    },
}


class RegexClassifier:
    """
    Regex-based classification using pattern matching.

    Provides high-precision detection of known sensitive data patterns.
    """

    def __init__(self):
        """Initialize regex classifier"""
        self.patterns = self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for efficiency"""
        compiled = {}
        for name, config in REGEX_PATTERNS.items():
            try:
                compiled[name] = {
                    "regex": re.compile(config["pattern"], re.IGNORECASE),
                    "label": config["label"],
                    "sublabel": config["sublabel"],
                    "confidence": config["confidence"],
                }
            except re.error as e:
                logger.error(f"Invalid regex pattern for {name}: {e}")
        return compiled

    def classify(self, text: str, classification_types: Optional[List[str]] = None) -> List[Entity]:
        """
        Classify text using regex patterns.

        Args:
            text: Text to classify
            classification_types: Types to look for (PII, PHI, etc.)

        Returns:
            List of detected entities
        """
        entities = []

        for name, pattern_config in self.patterns.items():
            # Skip if not in requested classification types
            if classification_types and pattern_config["label"] not in classification_types:
                continue

            try:
                for match in pattern_config["regex"].finditer(text):
                    entity = Entity(
                        text=match.group(),
                        start=match.start(),
                        end=match.end(),
                        label=pattern_config["label"],
                        sublabel=pattern_config["sublabel"],
                        confidence=pattern_config["confidence"],
                        source=EntitySource.REGEX,
                        metadata={
                            "pattern_name": name,
                        },
                    )
                    entities.append(entity)

            except Exception as e:
                logger.error(f"Error matching pattern {name}: {e}")

        return entities

    def add_pattern(self, name: str, pattern: str, label: str, sublabel: str, confidence: float):
        """
        Add a custom regex pattern.

        Args:
            name: Pattern name
            pattern: Regex pattern string
            label: Classification label (PII, PHI, etc.)
            sublabel: Specific type
            confidence: Confidence score (0.0-1.0)
        """
        try:
            self.patterns[name] = {
                "regex": re.compile(pattern, re.IGNORECASE),
                "label": label,
                "sublabel": sublabel,
                "confidence": confidence,
            }
            logger.info(f"Added custom pattern: {name}")
        except re.error as e:
            logger.error(f"Invalid regex pattern for {name}: {e}")
            raise ValueError(f"Invalid regex pattern: {e}")

    def get_pattern_names(self) -> List[str]:
        """Get list of available pattern names"""
        return list(self.patterns.keys())
