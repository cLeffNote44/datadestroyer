"""
Result merging logic for hybrid classification.

Combines results from regex and ML classifiers, handling overlaps
and calculating final confidence scores.
"""

import logging
from typing import List

from .entities import ConfidenceConfig, Entity

logger = logging.getLogger(__name__)


class ResultMerger:
    """
    Merges classification results from multiple sources.

    Handles overlapping entities, deduplication, and confidence calculation.
    """

    def __init__(self, config: ConfidenceConfig = None):
        """
        Initialize result merger.

        Args:
            config: Configuration for confidence scoring
        """
        self.config = config or ConfidenceConfig()

    def merge(
        self,
        regex_entities: List[Entity],
        ml_entities: List[Entity],
    ) -> List[Entity]:
        """
        Merge entities from regex and ML classifiers.

        Strategy:
        1. Find exact matches (same span) -> boost confidence
        2. Find overlapping entities -> keep higher confidence
        3. Keep non-overlapping entities from both
        4. Sort by position in text

        Args:
            regex_entities: Entities from regex classifier
            ml_entities: Entities from ML classifier

        Returns:
            Merged list of entities
        """
        merged = []

        # Track which entities have been merged
        used_regex = set()
        used_ml = set()

        # Find exact matches (same span)
        for i, regex_ent in enumerate(regex_entities):
            for j, ml_ent in enumerate(ml_entities):
                if self._same_span(regex_ent, ml_ent):
                    # Both methods found same entity - high confidence!
                    merged_ent = self._merge_matching_entities(regex_ent, ml_ent)
                    merged.append(merged_ent)
                    used_regex.add(i)
                    used_ml.add(j)
                    logger.debug(f"Exact match found: {merged_ent.text}")

        # Find overlapping entities
        for i, regex_ent in enumerate(regex_entities):
            if i in used_regex:
                continue

            for j, ml_ent in enumerate(ml_entities):
                if j in used_ml:
                    continue

                if regex_ent.overlaps_with(ml_ent):
                    # Overlapping but not exact match
                    merged_ent = self._merge_overlapping_entities(regex_ent, ml_ent)
                    merged.append(merged_ent)
                    used_regex.add(i)
                    used_ml.add(j)
                    logger.debug(f"Overlap found: {merged_ent.text}")

        # Add remaining regex entities (high precision)
        for i, regex_ent in enumerate(regex_entities):
            if i not in used_regex:
                # Regex matches are high confidence by default
                merged.append(regex_ent)

        # Add remaining ML entities (if confidence above threshold)
        for j, ml_ent in enumerate(ml_entities):
            if j not in used_ml and ml_ent.confidence >= self.config.minimum_threshold:
                merged.append(ml_ent)

        # Remove duplicates and sort by position
        merged = self._deduplicate(merged)
        merged.sort(key=lambda e: e.start)

        return merged

    def _same_span(self, entity1: Entity, entity2: Entity) -> bool:
        """Check if two entities have the same span"""
        return entity1.start == entity2.start and entity1.end == entity2.end

    def _merge_matching_entities(self, regex_ent: Entity, ml_ent: Entity) -> Entity:
        """
        Merge two entities with the same span.

        Both classifiers agree - boost confidence.
        """
        # Use regex label if they differ (regex is more specific)
        label = regex_ent.label
        sublabel = regex_ent.sublabel

        # Calculate boosted confidence
        confidence = min(
            1.0,
            max(regex_ent.confidence, ml_ent.confidence) + self.config.agreement_boost,
        )

        # Combine metadata
        metadata = {
            **regex_ent.metadata,
            **ml_ent.metadata,
            "agreement": True,
            "regex_confidence": regex_ent.confidence,
            "ml_confidence": ml_ent.confidence,
        }

        from .entities import EntitySource

        return Entity(
            text=regex_ent.text,
            start=regex_ent.start,
            end=regex_ent.end,
            label=label,
            sublabel=sublabel,
            confidence=confidence,
            source=EntitySource.HYBRID,
            metadata=metadata,
        )

    def _merge_overlapping_entities(self, regex_ent: Entity, ml_ent: Entity) -> Entity:
        """
        Merge two overlapping entities.

        Choose based on confidence and specificity.
        """
        # Prefer regex if similar confidence (regex is more specific)
        if abs(regex_ent.confidence - ml_ent.confidence) < 0.1:
            base_entity = regex_ent
            other_entity = ml_ent
        else:
            # Choose higher confidence
            base_entity = regex_ent if regex_ent.confidence > ml_ent.confidence else ml_ent
            other_entity = ml_ent if regex_ent.confidence > ml_ent.confidence else regex_ent

        # Combine metadata
        metadata = {
            **base_entity.metadata,
            "overlap": True,
            "other_source": other_entity.source.value,
            "other_confidence": other_entity.confidence,
        }

        return Entity(
            text=base_entity.text,
            start=base_entity.start,
            end=base_entity.end,
            label=base_entity.label,
            sublabel=base_entity.sublabel,
            confidence=base_entity.confidence,
            source=base_entity.source,
            metadata=metadata,
        )

    def _deduplicate(self, entities: List[Entity]) -> List[Entity]:
        """
        Remove duplicate entities.

        Keeps entity with highest confidence if duplicates found.
        """
        if not entities:
            return []

        # Sort by confidence (descending)
        sorted_entities = sorted(entities, key=lambda e: e.confidence, reverse=True)

        deduplicated = []
        used_spans = set()

        for entity in sorted_entities:
            span = (entity.start, entity.end)
            if span not in used_spans:
                deduplicated.append(entity)
                used_spans.add(span)

        return deduplicated

    def calculate_overall_confidence(self, entities: List[Entity]) -> float:
        """
        Calculate overall confidence for a classification result.

        Args:
            entities: List of entities

        Returns:
            Overall confidence score (0.0-1.0)
        """
        if not entities:
            return 0.0

        # Weighted average based on confidence and number of entities
        total_confidence = sum(e.confidence for e in entities)
        avg_confidence = total_confidence / len(entities)

        # Boost if multiple high-confidence entities found
        high_conf_count = sum(1 for e in entities if e.confidence >= self.config.high_threshold)
        if high_conf_count > 1:
            avg_confidence = min(1.0, avg_confidence + 0.05)

        return avg_confidence
