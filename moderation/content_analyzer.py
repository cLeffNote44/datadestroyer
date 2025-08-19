"""
Content Analysis Engine for detecting PII and sensitive information.

This module provides comprehensive pattern-based detection of:
- Personal Identifiable Information (PII)
- Financial data (credit cards, bank accounts)
- Medical information (insurance IDs, medical records)
- Legal references (case numbers, court documents)
- Custom user-defined sensitive patterns
"""

import re
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from django.contrib.contenttypes.models import ContentType

from .models import ContentScan, PolicyViolation, SensitiveContentPattern, SensitivityLevel


class PatternCategory(Enum):
    """Categories of built-in detection patterns"""

    PII = "pii"
    FINANCIAL = "financial"
    MEDICAL = "medical"
    LEGAL = "legal"
    CUSTOM = "custom"


@dataclass
class DetectionResult:
    """Result of a content analysis operation"""

    pattern_name: str
    pattern_type: str
    sensitivity: str
    matches: List[str]
    match_count: int
    context_snippets: List[str]
    positions: List[Tuple[int, int]]  # (start, end) positions


@dataclass
class ScanResult:
    """Overall result of scanning a piece of content"""

    content_length: int
    processing_time_ms: int
    violations_found: int
    highest_severity: Optional[str]
    scan_score: int
    detections: List[DetectionResult]
    total_matches: int


class BuiltInPatterns:
    """Built-in regex patterns for common PII and sensitive data"""

    # Social Security Numbers (various formats)
    SSN_PATTERNS = {
        "ssn_standard": r"\b\d{3}-\d{2}-\d{4}\b",
        "ssn_no_dashes": r"\b\d{9}\b",
        "ssn_spaces": r"\b\d{3}\s\d{2}\s\d{4}\b",
    }

    # Credit Card Numbers
    CREDIT_CARD_PATTERNS = {
        "visa": r"\b4\d{3}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b",
        "mastercard": r"\b5[1-5]\d{2}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b",
        "amex": r"\b3[47]\d{2}[\s\-]?\d{6}[\s\-]?\d{5}\b",
        "discover": r"\b6(?:011|5\d{2})[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b",
    }

    # Phone Numbers
    PHONE_PATTERNS = {
        "us_phone": r"\b(?:\+1[\s\-]?)?\(?([2-9]\d{2})\)?[\s\-]?([2-9]\d{2})[\s\-]?(\d{4})\b",
        "international": r"\b\+\d{1,3}[\s\-]?\d{1,14}\b",
    }

    # Email addresses
    EMAIL_PATTERNS = {
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    }

    # Driver's License patterns (US states)
    DRIVERS_LICENSE_PATTERNS = {
        "ca_license": r"\b[A-Z]\d{7}\b",  # California
        "ny_license": r"\b\d{3}[\s\-]?\d{3}[\s\-]?\d{3}\b",  # New York
        "fl_license": r"\b[A-Z]\d{3}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{3}[\s\-]?\d\b",  # Florida
    }

    # Banking information
    BANKING_PATTERNS = {
        "routing_number": r"\b[0-9]{9}\b",  # US routing numbers
        "account_number": r"\b\d{8,17}\b",  # Bank account numbers (approximate)
        "iban": r"\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}([A-Z0-9]?){0,16}\b",  # International
    }

    # Medical identifiers
    MEDICAL_PATTERNS = {
        "insurance_id": r"\b[A-Z]{2,4}\d{6,12}\b",
        "medicare_number": r"\b\d{3}-\d{2}-\d{4}[A-Z]?\b",
        "npi_number": r"\b\d{10}\b",  # National Provider Identifier
        "medical_record": r"\bMRN[\s\-]?\d{6,10}\b",
    }

    # Legal references
    LEGAL_PATTERNS = {
        "case_number": r"\b\d{2,4}[\s\-]?[A-Z]{2,4}[\s\-]?\d{4,8}\b",
        "docket_number": r"\bNo\.?\s*\d{2,4}[\s\-]\d{4,8}\b",
        "court_case": r"\bv\.?\s+[A-Z][a-z]+\b",  # Case names like "v. Smith"
    }

    # Government IDs
    GOVERNMENT_ID_PATTERNS = {
        "passport": r"\b[A-Z]{1,2}\d{6,9}\b",
        "ein": r"\b\d{2}-\d{7}\b",  # Employer Identification Number
        "itin": r"\b9\d{2}-\d{2}-\d{4}\b",  # Individual Taxpayer Identification Number
    }

    @classmethod
    def get_all_patterns(cls) -> Dict[str, Dict[str, str]]:
        """Get all built-in patterns organized by category"""
        return {
            "pii": {
                **cls.SSN_PATTERNS,
                **cls.PHONE_PATTERNS,
                **cls.EMAIL_PATTERNS,
                **cls.DRIVERS_LICENSE_PATTERNS,
                **cls.GOVERNMENT_ID_PATTERNS,
            },
            "financial": {
                **cls.CREDIT_CARD_PATTERNS,
                **cls.BANKING_PATTERNS,
            },
            "medical": cls.MEDICAL_PATTERNS,
            "legal": cls.LEGAL_PATTERNS,
        }


class ContentAnalyzer:
    """Main content analysis engine"""

    def __init__(self):
        self.active_patterns = None
        self._load_patterns()

    def _load_patterns(self):
        """Load active patterns from database"""
        self.active_patterns = list(
            SensitiveContentPattern.objects.filter(is_active=True).select_related()
        )

    def refresh_patterns(self):
        """Reload patterns from database"""
        self._load_patterns()

    def analyze_content(self, content: str, user_sensitivity: str = "medium") -> ScanResult:
        """
        Analyze content for sensitive information

        Args:
            content: Text content to analyze
            user_sensitivity: User's sensitivity preference

        Returns:
            ScanResult with detailed analysis
        """
        start_time = time.time()
        detections = []
        total_matches = 0
        highest_severity = None

        # Convert content to string if it's not already
        if not isinstance(content, str):
            content = str(content)

        content_length = len(content)

        # Apply each active pattern
        for pattern in self.active_patterns:
            # Skip patterns below user's sensitivity threshold
            if self._is_below_threshold(pattern.sensitivity_level, user_sensitivity):
                continue

            detection = self._test_pattern(pattern, content)
            if detection.matches:
                detections.append(detection)
                total_matches += detection.match_count

                # Track highest severity
                if highest_severity is None or self._severity_rank(
                    detection.sensitivity
                ) > self._severity_rank(highest_severity):
                    highest_severity = detection.sensitivity

        processing_time_ms = int((time.time() - start_time) * 1000)

        return ScanResult(
            content_length=content_length,
            processing_time_ms=processing_time_ms,
            violations_found=len(detections),
            highest_severity=highest_severity,
            scan_score=self._calculate_scan_score(detections, content_length),
            detections=detections,
            total_matches=total_matches,
        )

    def _test_pattern(self, pattern: SensitiveContentPattern, content: str) -> DetectionResult:
        """Test a single pattern against content"""
        matches = pattern.test_content(content)
        context_snippets = []
        positions = []

        if matches:
            # Find positions and context for each match
            flags = 0 if pattern.case_sensitive else re.IGNORECASE
            regex_pattern = pattern.regex_pattern

            if pattern.match_whole_words:
                regex_pattern = r"\\b" + regex_pattern + r"\\b"

            try:
                for match in re.finditer(regex_pattern, content, flags):
                    start, end = match.span()
                    positions.append((start, end))

                    # Extract context snippet (50 chars before/after)
                    context_start = max(0, start - 50)
                    context_end = min(len(content), end + 50)
                    context = content[context_start:context_end]

                    # Redact the sensitive part in context
                    match_text = content[start:end]
                    redacted_context = context.replace(match_text, "*" * len(match_text))
                    context_snippets.append(redacted_context)

            except re.error:
                # Pattern error - skip this match
                pass

        return DetectionResult(
            pattern_name=pattern.name,
            pattern_type=pattern.pattern_type,
            sensitivity=pattern.sensitivity_level,
            matches=matches,
            match_count=len(matches),
            context_snippets=context_snippets,
            positions=positions,
        )

    def _calculate_scan_score(self, detections: List[DetectionResult], content_length: int) -> int:
        """Calculate overall risk score (0-100) based on detections"""
        if not detections:
            return 0

        score = 0
        severity_weights = {
            SensitivityLevel.LOW: 10,
            SensitivityLevel.MEDIUM: 25,
            SensitivityLevel.HIGH: 50,
            SensitivityLevel.CRITICAL: 75,
        }

        for detection in detections:
            base_score = severity_weights.get(detection.sensitivity, 25)

            # Multiply by match count (but with diminishing returns)
            match_multiplier = min(detection.match_count * 0.5 + 0.5, 2.0)
            detection_score = base_score * match_multiplier

            score += detection_score

        # Normalize based on content length (more violations in short content = higher risk)
        if content_length > 0:
            density_factor = min(1000 / content_length, 2.0)  # Cap at 2x
            score *= density_factor

        return min(int(score), 100)

    def _severity_rank(self, severity: str) -> int:
        """Convert severity to numeric rank for comparison"""
        ranks = {
            SensitivityLevel.LOW: 1,
            SensitivityLevel.MEDIUM: 2,
            SensitivityLevel.HIGH: 3,
            SensitivityLevel.CRITICAL: 4,
        }
        return ranks.get(severity, 0)

    def _is_below_threshold(self, pattern_sensitivity: str, user_sensitivity: str) -> bool:
        """Check if pattern sensitivity is below user threshold"""
        return self._severity_rank(pattern_sensitivity) < self._severity_rank(user_sensitivity)

    def scan_and_store(
        self, content: str, content_object, user, scan_type: str = "automatic"
    ) -> ContentScan:
        """
        Analyze content and store results in database

        Args:
            content: Content to analyze
            content_object: Django model instance (Document, Message, Post, etc.)
            user: User who owns the content
            scan_type: Type of scan being performed

        Returns:
            ContentScan instance with stored results
        """
        # Get user's sensitivity preference
        user_settings = getattr(user, "moderation_settings", None)
        sensitivity = user_settings.scan_sensitivity if user_settings else SensitivityLevel.MEDIUM

        # Analyze content
        scan_result = self.analyze_content(content, sensitivity)

        # Create ContentScan record
        content_type = ContentType.objects.get_for_model(content_object)
        content_scan = ContentScan.objects.create(
            content_type=content_type,
            object_id=str(content_object.pk),
            user=user,
            scan_type=scan_type,
            violations_found=scan_result.violations_found,
            highest_severity=scan_result.highest_severity,
            scan_score=scan_result.scan_score,
            content_length=scan_result.content_length,
            processing_time_ms=scan_result.processing_time_ms,
            patterns_matched=[d.pattern_name for d in scan_result.detections],
        )

        # Create PolicyViolation records for each detection
        for detection in scan_result.detections:
            # Find the pattern object
            try:
                pattern = SensitiveContentPattern.objects.get(name=detection.pattern_name)

                # Create violation record
                PolicyViolation.objects.create(
                    content_scan=content_scan,
                    pattern=pattern,
                    violation_type=detection.pattern_type,
                    severity=detection.sensitivity,
                    matched_content="; ".join(detection.matches[:3]),  # Store first 3 matches
                    match_count=detection.match_count,
                    context_snippet="; ".join(detection.context_snippets[:2]),  # First 2 contexts
                )
            except SensitiveContentPattern.DoesNotExist:
                continue

        return content_scan


class ModerationEngine:
    """High-level moderation orchestration"""

    def __init__(self):
        self.analyzer = ContentAnalyzer()

    def process_content(self, content_object, user, content_text: str = None) -> Dict[str, Any]:
        """
        Complete moderation processing for a content object

        Returns:
            Dictionary with processing results and recommended actions
        """
        # Extract content text if not provided
        if content_text is None:
            content_text = self._extract_content_text(content_object)

        if not content_text:
            return {"status": "skipped", "reason": "No content to analyze"}

        # Perform scan
        content_scan = self.analyzer.scan_and_store(content_text, content_object, user)

        # Determine recommended actions
        actions = self._determine_actions(content_scan, user)

        return {
            "status": "completed",
            "scan_id": content_scan.id,
            "violations_found": content_scan.violations_found,
            "scan_score": content_scan.scan_score,
            "risk_level": content_scan.risk_level,
            "recommended_actions": actions,
            "processing_time_ms": content_scan.processing_time_ms,
        }

    def _extract_content_text(self, content_object) -> str:
        """Extract text content from various content types"""
        # Handle different content types
        if hasattr(content_object, "content"):
            return content_object.content
        elif hasattr(content_object, "description"):
            return content_object.description
        elif hasattr(content_object, "title"):
            return content_object.title
        else:
            return str(content_object)

    def _determine_actions(self, content_scan: ContentScan, user) -> List[Dict[str, Any]]:
        """Determine what actions should be taken based on scan results"""
        actions = []

        # Get user settings
        settings = getattr(user, "moderation_settings", None)

        if content_scan.scan_score >= 80:  # Critical risk
            actions.append(
                {
                    "type": "notify_user",
                    "priority": "high",
                    "message": "Critical privacy risk detected in your content",
                }
            )

            if settings and settings.auto_quarantine_critical:
                actions.append(
                    {
                        "type": "quarantine",
                        "reason": f"Automatic quarantine due to critical violations (score: {content_scan.scan_score})",
                    }
                )

        elif content_scan.scan_score >= 60:  # High risk
            actions.append(
                {
                    "type": "notify_user",
                    "priority": "medium",
                    "message": "High privacy risk detected - please review your content",
                }
            )

            if settings and settings.auto_block_sharing:
                actions.append(
                    {
                        "type": "block_sharing",
                        "reason": "Blocking sharing due to detected sensitive information",
                    }
                )

        elif content_scan.scan_score >= 40:  # Medium risk
            actions.append(
                {
                    "type": "notify_user",
                    "priority": "low",
                    "message": "Potential sensitive information detected",
                }
            )

        return actions


# Global analyzer instance
analyzer = ContentAnalyzer()
moderation_engine = ModerationEngine()


def analyze_content(content: str, user_sensitivity: str = "medium") -> ScanResult:
    """Convenience function for content analysis"""
    return analyzer.analyze_content(content, user_sensitivity)


def scan_content_object(content_object, user, content_text: str = None) -> Dict[str, Any]:
    """Convenience function for complete content moderation"""
    return moderation_engine.process_content(content_object, user, content_text)
