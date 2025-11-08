"""
Entity and result data structures for ML classification.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class EntitySource(str, Enum):
    """Source of entity detection"""

    REGEX = "regex"
    SPACY_NER = "spacy_ner"
    MEDICAL_NER = "medical_ner"
    TRANSFORMER = "transformer"
    HYBRID = "hybrid"


class ClassificationType(str, Enum):
    """Types of classification"""

    PII = "PII"
    PHI = "PHI"
    FINANCIAL = "Financial"
    IP = "IP"
    CONFIDENTIAL = "Confidential"


@dataclass
class Entity:
    """
    Represents a detected entity in text.

    Attributes:
        text: The actual text of the entity
        start: Start position in the original text
        end: End position in the original text
        label: Primary classification label (PII, PHI, etc.)
        sublabel: Specific entity type (PERSON, SSN, etc.)
        confidence: Confidence score (0.0-1.0)
        source: Detection method used
        metadata: Additional information about the entity
    """

    text: str
    start: int
    end: int
    label: str
    sublabel: str
    confidence: float
    source: EntitySource
    metadata: Dict = field(default_factory=dict)

    def __post_init__(self):
        """Validate entity data"""
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"Confidence must be between 0 and 1, got {self.confidence}")
        if self.end <= self.start:
            raise ValueError(f"End position ({self.end}) must be greater than start ({self.start})")

    def overlaps_with(self, other: "Entity") -> bool:
        """Check if this entity overlaps with another"""
        return not (self.end <= other.start or self.start >= other.end)

    def contains(self, other: "Entity") -> bool:
        """Check if this entity completely contains another"""
        return self.start <= other.start and self.end >= other.end

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "text": self.text,
            "start": self.start,
            "end": self.end,
            "label": self.label,
            "sublabel": self.sublabel,
            "confidence": self.confidence,
            "source": self.source.value,
            "metadata": self.metadata,
        }


@dataclass
class ClassificationResult:
    """
    Result of classification on a text.

    Attributes:
        text: Original text that was classified
        entities: List of detected entities
        classification_types: Types of classification performed
        regex_entities: Entities found by regex
        ml_entities: Entities found by ML
        overall_confidence: Overall confidence in the classification
        processing_time_ms: Time taken to process (milliseconds)
        metadata: Additional metadata
    """

    text: str
    entities: List[Entity]
    classification_types: List[str]
    regex_entities: List[Entity] = field(default_factory=list)
    ml_entities: List[Entity] = field(default_factory=list)
    overall_confidence: float = 0.0
    processing_time_ms: float = 0.0
    metadata: Dict = field(default_factory=dict)

    @property
    def has_entities(self) -> bool:
        """Check if any entities were found"""
        return len(self.entities) > 0

    @property
    def entity_count(self) -> int:
        """Total number of entities found"""
        return len(self.entities)

    @property
    def pii_entities(self) -> List[Entity]:
        """Get only PII entities"""
        return [e for e in self.entities if e.label == "PII"]

    @property
    def phi_entities(self) -> List[Entity]:
        """Get only PHI entities"""
        return [e for e in self.entities if e.label == "PHI"]

    @property
    def financial_entities(self) -> List[Entity]:
        """Get only Financial entities"""
        return [e for e in self.entities if e.label == "Financial"]

    def get_entities_by_label(self, label: str) -> List[Entity]:
        """Get entities by classification label"""
        return [e for e in self.entities if e.label == label]

    def get_entities_by_sublabel(self, sublabel: str) -> List[Entity]:
        """Get entities by specific type"""
        return [e for e in self.entities if e.sublabel == sublabel]

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "text": self.text,
            "entities": [e.to_dict() for e in self.entities],
            "classification_types": self.classification_types,
            "regex_entity_count": len(self.regex_entities),
            "ml_entity_count": len(self.ml_entities),
            "total_entity_count": self.entity_count,
            "overall_confidence": self.overall_confidence,
            "processing_time_ms": self.processing_time_ms,
            "metadata": self.metadata,
        }


@dataclass
class ConfidenceConfig:
    """
    Configuration for confidence scoring.

    Attributes:
        regex_base: Base confidence for regex matches
        ml_base: Base confidence for ML matches
        agreement_boost: Boost when both methods agree
        high_threshold: Threshold for high confidence
        minimum_threshold: Minimum confidence to include entity
    """

    regex_base: float = 0.95
    ml_base: float = 0.85
    agreement_boost: float = 0.05
    high_threshold: float = 0.90
    minimum_threshold: float = 0.60

    def __post_init__(self):
        """Validate configuration"""
        for attr, value in self.__dict__.items():
            if not 0 <= value <= 1:
                raise ValueError(f"{attr} must be between 0 and 1, got {value}")
