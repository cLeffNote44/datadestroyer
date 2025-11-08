"""
ML-based classifier using spaCy NER and transformers.
"""

import logging
from typing import List, Optional

from .entities import Entity, EntitySource

logger = logging.getLogger(__name__)


# Entity type mappings
SPACY_TO_CLASSIFICATION = {
    "PERSON": ("PII", "PERSON"),
    "ORG": ("PII", "ORGANIZATION"),
    "GPE": ("PII", "LOCATION"),
    "LOC": ("PII", "LOCATION"),
    "DATE": ("PII", "DATE"),
    "TIME": ("PII", "TIME"),
    "MONEY": ("Financial", "MONEY"),
    "CARDINAL": ("PII", "NUMBER"),
    "PERCENT": ("Financial", "PERCENT"),
}

MEDICAL_TO_CLASSIFICATION = {
    "DISEASE": ("PHI", "DISEASE"),
    "CHEMICAL": ("PHI", "MEDICATION"),
    "SYMPTOM": ("PHI", "SYMPTOM"),
    "PROCEDURE": ("PHI", "PROCEDURE"),
}


class MLClassifier:
    """
    ML-based classification using spaCy and other ML models.

    Uses pre-trained NER models to detect entities with context awareness.
    """

    def __init__(self, use_gpu: bool = False):
        """
        Initialize ML classifier.

        Args:
            use_gpu: Whether to use GPU for inference (if available)
        """
        self.use_gpu = use_gpu
        self.spacy_model = None
        self.medical_model = None
        self._models_loaded = False

    def load_models(self):
        """Load spaCy models lazily"""
        if self._models_loaded:
            return

        try:
            import spacy

            # Try to load transformer-based model (best accuracy)
            try:
                self.spacy_model = spacy.load("en_core_web_trf")
                logger.info("Loaded transformer-based spaCy model")
            except OSError:
                # Fall back to smaller model
                try:
                    self.spacy_model = spacy.load("en_core_web_sm")
                    logger.info("Loaded small spaCy model (transformer model not found)")
                except OSError:
                    logger.warning(
                        "No spaCy model found. Run: python -m spacy download en_core_web_sm"
                    )
                    self.spacy_model = None

            # Try to load medical NER model
            try:
                self.medical_model = spacy.load("en_ner_bc5cdr_md")
                logger.info("Loaded medical NER model")
            except OSError:
                logger.info("Medical NER model not found (optional)")
                self.medical_model = None

            self._models_loaded = True

        except ImportError:
            logger.error("spaCy not installed. Install with: pip install spacy")

    def classify(self, text: str, classification_types: Optional[List[str]] = None) -> List[Entity]:
        """
        Classify text using ML models.

        Args:
            text: Text to classify
            classification_types: Types to look for (PII, PHI, etc.)

        Returns:
            List of detected entities
        """
        if not self._models_loaded:
            self.load_models()

        entities = []

        # Extract PII using spaCy NER
        if classification_types is None or "PII" in classification_types or "Financial" in classification_types:
            entities.extend(self._extract_pii(text))

        # Extract PHI using medical NER
        if classification_types is None or "PHI" in classification_types:
            entities.extend(self._extract_phi(text))

        return entities

    def _extract_pii(self, text: str) -> List[Entity]:
        """
        Extract PII using spaCy NER.

        Args:
            text: Text to analyze

        Returns:
            List of PII entities
        """
        if not self.spacy_model:
            return []

        entities = []

        try:
            doc = self.spacy_model(text)

            for ent in doc.ents:
                if ent.label_ in SPACY_TO_CLASSIFICATION:
                    label, sublabel = SPACY_TO_CLASSIFICATION[ent.label_]

                    # Calculate confidence based on model confidence
                    # spaCy doesn't provide direct confidence, so we use heuristics
                    confidence = self._calculate_ner_confidence(ent, doc)

                    entity = Entity(
                        text=ent.text,
                        start=ent.start_char,
                        end=ent.end_char,
                        label=label,
                        sublabel=sublabel,
                        confidence=confidence,
                        source=EntitySource.SPACY_NER,
                        metadata={
                            "spacy_label": ent.label_,
                            "lemma": ent.lemma_,
                        },
                    )
                    entities.append(entity)

        except Exception as e:
            logger.error(f"Error in spaCy NER: {e}")

        return entities

    def _extract_phi(self, text: str) -> List[Entity]:
        """
        Extract PHI using medical NER model.

        Args:
            text: Text to analyze

        Returns:
            List of PHI entities
        """
        if not self.medical_model:
            return []

        entities = []

        try:
            doc = self.medical_model(text)

            for ent in doc.ents:
                if ent.label_ in MEDICAL_TO_CLASSIFICATION:
                    label, sublabel = MEDICAL_TO_CLASSIFICATION[ent.label_]

                    confidence = self._calculate_ner_confidence(ent, doc)

                    entity = Entity(
                        text=ent.text,
                        start=ent.start_char,
                        end=ent.end_char,
                        label=label,
                        sublabel=sublabel,
                        confidence=confidence,
                        source=EntitySource.MEDICAL_NER,
                        metadata={
                            "medical_label": ent.label_,
                        },
                    )
                    entities.append(entity)

        except Exception as e:
            logger.error(f"Error in medical NER: {e}")

        return entities

    def _calculate_ner_confidence(self, ent, doc) -> float:
        """
        Calculate confidence score for NER entity.

        Since spaCy doesn't provide direct confidence scores,
        we use heuristics based on entity characteristics.

        Args:
            ent: spaCy entity
            doc: spaCy doc

        Returns:
            Confidence score (0.0-1.0)
        """
        base_confidence = 0.85

        # Boost confidence for longer entities
        if len(ent.text) > 10:
            base_confidence += 0.05

        # Boost for capitalized entities (names, places)
        if ent.text[0].isupper():
            base_confidence += 0.03

        # Reduce for very short entities
        if len(ent.text) < 3:
            base_confidence -= 0.10

        # Ensure within bounds
        return max(0.60, min(0.95, base_confidence))
