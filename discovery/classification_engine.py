"""
Intelligent Data Classification Engine

This module provides advanced data classification capabilities including:
- Pattern-based classification using regex and keyword matching
- ML-based content classification
- Context-aware classification using data relationships
- Confidence scoring and rule validation
"""

import hashlib
import json
import logging
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .models import (
    ClassificationConfidence,
    ClassificationResult,
    ClassificationRule,
    DataAsset,
    DataClassification,
)

logger = logging.getLogger(__name__)


@dataclass
class ClassificationMatch:
    """Represents a classification match result"""

    rule_name: str
    rule_id: int
    classification: str
    sensitivity: str
    confidence_score: float
    matched_patterns: List[str]
    context_data: Dict[str, Any]


@dataclass
class ContentContext:
    """Context information about the content being classified"""

    content_type: str
    field_name: Optional[str] = None
    model_name: Optional[str] = None
    app_name: Optional[str] = None
    related_data: Optional[Dict[str, Any]] = None
    size_bytes: Optional[int] = None
    file_extension: Optional[str] = None


class DataClassificationEngine:
    """Advanced data classification engine with multiple detection methods"""

    def __init__(self):
        self.rules_cache = {}
        self.pattern_cache = {}
        self.ml_models = {}
        self.context_analyzers = {}
        self._load_classification_rules()
        self._initialize_ml_models()

    def _load_classification_rules(self):
        """Load and cache active classification rules"""
        try:
            rules = ClassificationRule.objects.filter(is_active=True).order_by("priority")

            self.rules_cache = {
                "regex": [],
                "keyword": [],
                "ml_model": [],
                "context": [],
                "composite": [],
            }

            for rule in rules:
                rule_data = {
                    "id": rule.id,
                    "name": rule.name,
                    "pattern": rule.pattern,
                    "classification": rule.target_classification,
                    "sensitivity": rule.target_sensitivity,
                    "confidence_threshold": rule.confidence_threshold,
                    "priority": rule.priority,
                }
                self.rules_cache[rule.rule_type].append(rule_data)

            logger.info(
                f"Loaded {sum(len(rules) for rules in self.rules_cache.values())} classification rules"
            )

        except Exception as e:
            logger.error(f"Error loading classification rules: {e}")

    def _initialize_ml_models(self):
        """Initialize ML models for classification (placeholder for future ML integration)"""
        # Placeholder for ML model initialization
        # In a full implementation, this would load trained models for:
        # - Text classification models
        # - Named entity recognition models
        # - Pattern detection models
        pass

    def classify_content(
        self,
        content: str,
        context: Optional[ContentContext] = None,
        rules_to_apply: Optional[List[str]] = None,
    ) -> List[ClassificationMatch]:
        """
        Classify content using all available classification methods

        Args:
            content: The content to classify
            context: Optional context information about the content
            rules_to_apply: Optional list of specific rule names to apply

        Returns:
            List of classification matches with confidence scores
        """
        matches = []

        if not content or not content.strip():
            return matches

        try:
            # Apply different classification methods
            matches.extend(self._apply_regex_rules(content, context, rules_to_apply))
            matches.extend(self._apply_keyword_rules(content, context, rules_to_apply))
            matches.extend(self._apply_ml_classification(content, context, rules_to_apply))
            matches.extend(self._apply_context_classification(content, context, rules_to_apply))
            matches.extend(self._apply_composite_rules(content, context, rules_to_apply))

            # Remove duplicates and sort by confidence
            matches = self._deduplicate_matches(matches)
            matches.sort(key=lambda x: x.confidence_score, reverse=True)

            logger.debug(
                f"Classification found {len(matches)} matches for content of length {len(content)}"
            )

        except Exception as e:
            logger.error(f"Error during content classification: {e}")

        return matches

    def _apply_regex_rules(
        self, content: str, context: Optional[ContentContext], rules_to_apply: Optional[List[str]]
    ) -> List[ClassificationMatch]:
        """Apply regex-based classification rules"""
        matches = []

        for rule in self.rules_cache.get("regex", []):
            if rules_to_apply and rule["name"] not in rules_to_apply:
                continue

            try:
                pattern = rule["pattern"]
                compiled_pattern = self._get_compiled_pattern(pattern)

                found_matches = compiled_pattern.findall(content)

                if found_matches:
                    # Calculate confidence based on match quality
                    confidence = self._calculate_regex_confidence(
                        found_matches, content, pattern, context
                    )

                    if confidence >= rule["confidence_threshold"]:
                        matches.append(
                            ClassificationMatch(
                                rule_name=rule["name"],
                                rule_id=rule["id"],
                                classification=rule["classification"],
                                sensitivity=rule["sensitivity"],
                                confidence_score=confidence,
                                matched_patterns=[
                                    str(match) for match in found_matches[:5]
                                ],  # Limit for privacy
                                context_data={"rule_type": "regex", "pattern_type": "regex"},
                            )
                        )

            except Exception as e:
                logger.error(f"Error applying regex rule {rule['name']}: {e}")

        return matches

    def _apply_keyword_rules(
        self, content: str, context: Optional[ContentContext], rules_to_apply: Optional[List[str]]
    ) -> List[ClassificationMatch]:
        """Apply keyword-based classification rules"""
        matches = []

        for rule in self.rules_cache.get("keyword", []):
            if rules_to_apply and rule["name"] not in rules_to_apply:
                continue

            try:
                keywords = json.loads(rule["pattern"])
                if not isinstance(keywords, list):
                    continue

                content_lower = content.lower()
                found_keywords = []

                for keyword in keywords:
                    if isinstance(keyword, str) and keyword.lower() in content_lower:
                        found_keywords.append(keyword)

                if found_keywords:
                    confidence = self._calculate_keyword_confidence(
                        found_keywords, keywords, content, context
                    )

                    if confidence >= rule["confidence_threshold"]:
                        matches.append(
                            ClassificationMatch(
                                rule_name=rule["name"],
                                rule_id=rule["id"],
                                classification=rule["classification"],
                                sensitivity=rule["sensitivity"],
                                confidence_score=confidence,
                                matched_patterns=found_keywords[:5],  # Limit for privacy
                                context_data={
                                    "rule_type": "keyword",
                                    "total_keywords": len(keywords),
                                },
                            )
                        )

            except Exception as e:
                logger.error(f"Error applying keyword rule {rule['name']}: {e}")

        return matches

    def _apply_ml_classification(
        self, content: str, context: Optional[ContentContext], rules_to_apply: Optional[List[str]]
    ) -> List[ClassificationMatch]:
        """Apply ML-based classification (placeholder for future implementation)"""
        matches = []

        # Placeholder for ML-based classification
        # This would integrate with trained models to classify content
        # For now, we'll implement some basic heuristic classification

        for rule in self.rules_cache.get("ml_model", []):
            if rules_to_apply and rule["name"] not in rules_to_apply:
                continue

            try:
                # Placeholder ML logic - would be replaced with actual model inference
                confidence = self._heuristic_ml_classification(content, rule, context)

                if confidence >= rule["confidence_threshold"]:
                    matches.append(
                        ClassificationMatch(
                            rule_name=rule["name"],
                            rule_id=rule["id"],
                            classification=rule["classification"],
                            sensitivity=rule["sensitivity"],
                            confidence_score=confidence,
                            matched_patterns=["ml_model_prediction"],
                            context_data={"rule_type": "ml_model", "model_type": "heuristic"},
                        )
                    )

            except Exception as e:
                logger.error(f"Error applying ML rule {rule['name']}: {e}")

        return matches

    def _apply_context_classification(
        self, content: str, context: Optional[ContentContext], rules_to_apply: Optional[List[str]]
    ) -> List[ClassificationMatch]:
        """Apply context-aware classification rules"""
        matches = []

        if not context:
            return matches

        for rule in self.rules_cache.get("context", []):
            if rules_to_apply and rule["name"] not in rules_to_apply:
                continue

            try:
                context_config = json.loads(rule["pattern"])
                confidence = self._evaluate_context_rule(content, context, context_config)

                if confidence >= rule["confidence_threshold"]:
                    matches.append(
                        ClassificationMatch(
                            rule_name=rule["name"],
                            rule_id=rule["id"],
                            classification=rule["classification"],
                            sensitivity=rule["sensitivity"],
                            confidence_score=confidence,
                            matched_patterns=["context_match"],
                            context_data={
                                "rule_type": "context",
                                "context_factors": context_config,
                            },
                        )
                    )

            except Exception as e:
                logger.error(f"Error applying context rule {rule['name']}: {e}")

        return matches

    def _apply_composite_rules(
        self, content: str, context: Optional[ContentContext], rules_to_apply: Optional[List[str]]
    ) -> List[ClassificationMatch]:
        """Apply composite rules that combine multiple classification methods"""
        matches = []

        for rule in self.rules_cache.get("composite", []):
            if rules_to_apply and rule["name"] not in rules_to_apply:
                continue

            try:
                composite_config = json.loads(rule["pattern"])
                confidence = self._evaluate_composite_rule(content, context, composite_config)

                if confidence >= rule["confidence_threshold"]:
                    matches.append(
                        ClassificationMatch(
                            rule_name=rule["name"],
                            rule_id=rule["id"],
                            classification=rule["classification"],
                            sensitivity=rule["sensitivity"],
                            confidence_score=confidence,
                            matched_patterns=["composite_match"],
                            context_data={"rule_type": "composite", "components": composite_config},
                        )
                    )

            except Exception as e:
                logger.error(f"Error applying composite rule {rule['name']}: {e}")

        return matches

    def _get_compiled_pattern(self, pattern: str) -> re.Pattern:
        """Get compiled regex pattern with caching"""
        pattern_hash = hashlib.md5(pattern.encode()).hexdigest()

        if pattern_hash not in self.pattern_cache:
            try:
                self.pattern_cache[pattern_hash] = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            except re.error as e:
                logger.error(f"Invalid regex pattern '{pattern}': {e}")
                # Return a pattern that never matches
                self.pattern_cache[pattern_hash] = re.compile(r"(?!.*)")

        return self.pattern_cache[pattern_hash]

    def _calculate_regex_confidence(
        self, matches: List[str], content: str, pattern: str, context: Optional[ContentContext]
    ) -> float:
        """Calculate confidence score for regex matches"""
        if not matches:
            return 0.0

        # Base confidence from number of matches
        base_confidence = min(0.5 + (len(matches) * 0.1), 0.9)

        # Adjust based on match length and quality
        avg_match_length = sum(len(str(match)) for match in matches) / len(matches)
        length_factor = min(avg_match_length / 10, 1.0)

        # Context boost
        context_boost = 0.0
        if context:
            if context.field_name and any(
                indicator in context.field_name.lower()
                for indicator in ["ssn", "social", "credit", "card", "phone", "email"]
            ):
                context_boost = 0.15

        return min(base_confidence + (length_factor * 0.2) + context_boost, 1.0)

    def _calculate_keyword_confidence(
        self,
        found_keywords: List[str],
        all_keywords: List[str],
        content: str,
        context: Optional[ContentContext],
    ) -> float:
        """Calculate confidence score for keyword matches"""
        if not found_keywords:
            return 0.0

        # Base confidence from keyword match ratio
        match_ratio = len(found_keywords) / len(all_keywords)
        base_confidence = min(0.3 + (match_ratio * 0.5), 0.8)

        # Boost for exact keyword density
        content_words = len(content.split())
        keyword_density = len(found_keywords) / max(content_words, 1)
        density_boost = min(keyword_density * 2, 0.2)

        return min(base_confidence + density_boost, 1.0)

    def _heuristic_ml_classification(
        self, content: str, rule: Dict[str, Any], context: Optional[ContentContext]
    ) -> float:
        """Placeholder heuristic ML classification (to be replaced with actual ML models)"""
        # This is a simple heuristic classifier that would be replaced with trained models

        # Parse the ML rule configuration
        try:
            ml_config = json.loads(rule["pattern"])
        except:
            return 0.0

        target_class = rule["classification"]
        confidence = 0.0

        # Simple heuristics based on content characteristics
        if target_class == DataClassification.PII:
            # Look for PII-like patterns
            pii_indicators = [
                r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
                r"\b\d{10,15}\b",  # Phone numbers
                r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",  # Credit card
            ]
            matches = sum(1 for pattern in pii_indicators if re.search(pattern, content))
            confidence = min(matches * 0.3, 0.9)

        elif target_class == DataClassification.FINANCIAL:
            # Financial data indicators
            financial_terms = ["bank", "account", "routing", "balance", "transaction", "payment"]
            found_terms = sum(1 for term in financial_terms if term.lower() in content.lower())
            confidence = min(found_terms * 0.2, 0.8)

        elif target_class == DataClassification.PHI:
            # Medical/health indicators
            medical_terms = ["patient", "diagnosis", "treatment", "medical", "health", "doctor"]
            found_terms = sum(1 for term in medical_terms if term.lower() in content.lower())
            confidence = min(found_terms * 0.15, 0.7)

        return confidence

    def _evaluate_context_rule(
        self, content: str, context: ContentContext, context_config: Dict[str, Any]
    ) -> float:
        """Evaluate context-based classification rule"""
        confidence = 0.0

        # Check model/app context
        if "target_apps" in context_config and context.app_name:
            if context.app_name in context_config["target_apps"]:
                confidence += 0.3

        if "target_models" in context_config and context.model_name:
            if context.model_name in context_config["target_models"]:
                confidence += 0.4

        # Check field name patterns
        if "field_patterns" in context_config and context.field_name:
            for pattern in context_config["field_patterns"]:
                if re.search(pattern, context.field_name, re.IGNORECASE):
                    confidence += 0.3
                    break

        # Check content size thresholds
        if "size_thresholds" in context_config and context.size_bytes:
            thresholds = context_config["size_thresholds"]
            if (
                thresholds.get("min", 0)
                <= context.size_bytes
                <= thresholds.get("max", float("inf"))
            ):
                confidence += 0.2

        return min(confidence, 1.0)

    def _evaluate_composite_rule(
        self, content: str, context: Optional[ContentContext], composite_config: Dict[str, Any]
    ) -> float:
        """Evaluate composite rule that combines multiple methods"""
        total_confidence = 0.0
        weight_sum = 0.0

        # Apply each component rule
        for component in composite_config.get("components", []):
            component_type = component.get("type")
            weight = component.get("weight", 1.0)

            component_confidence = 0.0

            if component_type == "regex":
                pattern = component.get("pattern", "")
                try:
                    compiled_pattern = self._get_compiled_pattern(pattern)
                    matches = compiled_pattern.findall(content)
                    if matches:
                        component_confidence = self._calculate_regex_confidence(
                            matches, content, pattern, context
                        )
                except:
                    pass

            elif component_type == "keyword":
                keywords = component.get("keywords", [])
                found = [k for k in keywords if k.lower() in content.lower()]
                if found:
                    component_confidence = self._calculate_keyword_confidence(
                        found, keywords, content, context
                    )

            elif component_type == "context" and context:
                context_rules = component.get("rules", {})
                component_confidence = self._evaluate_context_rule(content, context, context_rules)

            total_confidence += component_confidence * weight
            weight_sum += weight

        # Calculate weighted average
        if weight_sum > 0:
            return min(total_confidence / weight_sum, 1.0)

        return 0.0

    def _deduplicate_matches(self, matches: List[ClassificationMatch]) -> List[ClassificationMatch]:
        """Remove duplicate matches, keeping the highest confidence for each rule"""
        seen_rules = {}

        for match in matches:
            rule_key = f"{match.rule_id}_{match.classification}_{match.sensitivity}"

            if (
                rule_key not in seen_rules
                or match.confidence_score > seen_rules[rule_key].confidence_score
            ):
                seen_rules[rule_key] = match

        return list(seen_rules.values())

    def get_confidence_level(self, confidence_score: float) -> str:
        """Convert confidence score to confidence level"""
        if confidence_score >= 0.95:
            return ClassificationConfidence.VERY_HIGH
        elif confidence_score >= 0.80:
            return ClassificationConfidence.HIGH
        elif confidence_score >= 0.60:
            return ClassificationConfidence.MEDIUM
        else:
            return ClassificationConfidence.LOW

    def classify_and_store_results(
        self,
        content: str,
        data_asset: DataAsset,
        discovery_job: Optional["DiscoveryJob"] = None,
        context: Optional[ContentContext] = None,
    ) -> List[ClassificationResult]:
        """Classify content and store results in database"""
        matches = self.classify_content(content, context)
        results = []

        for match in matches:
            try:
                # Get or create the classification result
                result, created = ClassificationResult.objects.get_or_create(
                    data_asset=data_asset,
                    classification_rule_id=match.rule_id,
                    defaults={
                        "discovery_job": discovery_job,
                        "predicted_classification": match.classification,
                        "predicted_sensitivity": match.sensitivity,
                        "confidence_score": match.confidence_score,
                        "confidence_level": self.get_confidence_level(match.confidence_score),
                        "matched_patterns": match.matched_patterns,
                        "context_information": match.context_data,
                    },
                )

                if not created:
                    # Update existing result if confidence is higher
                    if match.confidence_score > result.confidence_score:
                        result.confidence_score = match.confidence_score
                        result.confidence_level = self.get_confidence_level(match.confidence_score)
                        result.matched_patterns = match.matched_patterns
                        result.context_information = match.context_data
                        result.save()

                results.append(result)

            except Exception as e:
                logger.error(f"Error storing classification result: {e}")

        return results

    def refresh_rules(self):
        """Refresh cached classification rules"""
        self._load_classification_rules()
        # Clear pattern cache to ensure new patterns are compiled
        self.pattern_cache.clear()

    def get_classification_summary(self, data_asset: DataAsset) -> Dict[str, Any]:
        """Get a summary of classification results for a data asset"""
        results = ClassificationResult.objects.filter(data_asset=data_asset)

        if not results.exists():
            return {
                "total_classifications": 0,
                "highest_confidence": 0.0,
                "primary_classification": None,
                "sensitivity_level": None,
                "confidence_level": None,
            }

        # Get the highest confidence result
        top_result = results.order_by("-confidence_score").first()

        # Count classifications by type
        classification_counts = Counter(result.predicted_classification for result in results)

        return {
            "total_classifications": results.count(),
            "highest_confidence": top_result.confidence_score,
            "primary_classification": top_result.predicted_classification,
            "sensitivity_level": top_result.predicted_sensitivity,
            "confidence_level": top_result.confidence_level,
            "classification_distribution": dict(classification_counts),
            "validated_results": results.filter(is_validated=True).count(),
        }


# Global instance
classification_engine = DataClassificationEngine()
