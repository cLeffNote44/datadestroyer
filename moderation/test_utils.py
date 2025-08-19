"""
Test utilities for moderation tests.

Provides helper functions to create test data for the moderation system.
"""

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from .models import (
    ContentScan,
    PolicyViolation,
    SensitiveContentPattern,
    SensitivityLevel,
    ViolationType,
)

User = get_user_model()


def create_test_content_scan(user, **kwargs):
    """Create a test content scan with all required fields populated.

    Args:
        user: The user to associate with the scan
        **kwargs: Additional fields to set on the ContentScan

    Returns:
        ContentScan: The created content scan
    """
    # Get a ContentType for User as a test subject
    user_content_type = ContentType.objects.get_for_model(User)

    # Default values
    defaults = {
        "content_type": user_content_type,
        "object_id": str(user.id),
        "user": user,
        "content_length": 100,
        "processing_time_ms": 50,
        "patterns_matched": [],
        "violations_found": 0,
        "scan_score": 0,
        "highest_severity": None,
    }

    # Override with provided values
    defaults.update(kwargs)

    return ContentScan.objects.create(**defaults)


def create_test_violation(content_scan, pattern, **kwargs):
    """Create a test policy violation.

    Args:
        content_scan: The ContentScan to associate with
        pattern: The SensitiveContentPattern that matched
        **kwargs: Additional fields to set on the PolicyViolation

    Returns:
        PolicyViolation: The created violation
    """
    # Default values
    defaults = {
        "content_scan": content_scan,
        "pattern": pattern,
        "violation_type": pattern.pattern_type,
        "severity": pattern.sensitivity_level,
        "matched_content": "test-content",
        "context_snippet": "test context",
        "match_count": 1,
        "is_resolved": False,
    }

    # Override with provided values
    defaults.update(kwargs)

    return PolicyViolation.objects.create(**defaults)


def create_test_data_for_insights(user, pattern_count=5):
    """Create a full set of test data for testing insights.

    Args:
        user: The user to associate data with
        pattern_count: Number of patterns to include

    Returns:
        dict: A dictionary with created test objects
    """
    # Get or create patterns to use
    patterns = list(SensitiveContentPattern.objects.filter(is_active=True)[:pattern_count])
    if not patterns:
        raise ValueError(
            "No active patterns found. Run 'python manage.py load_builtin_patterns' first."
        )

    # Create content scan
    content_scan = create_test_content_scan(
        user,
        content_length=500,
        processing_time_ms=150,
        violations_found=5,
        highest_severity=SensitivityLevel.CRITICAL,
        scan_score=95,
    )

    violations = []

    # Create various violation types

    # PII violations
    for i, pattern in enumerate(patterns[:3]):
        violation = create_test_violation(
            content_scan=content_scan,
            pattern=pattern,
            violation_type=ViolationType.PII_DETECTED,
            severity=SensitivityLevel.HIGH,
            matched_content=f"test-data-{i}",
            context_snippet="Test violation context",
            is_resolved=False,
        )
        violations.append(violation)

    # Financial violation
    financial_violation = create_test_violation(
        content_scan=content_scan,
        pattern=patterns[0],
        violation_type=ViolationType.FINANCIAL_DATA,
        severity=SensitivityLevel.CRITICAL,
        matched_content="4532-1234-5678-9012",
        context_snippet="Credit card number detected",
        is_resolved=False,
    )
    violations.append(financial_violation)

    # Medical violation
    medical_violation = create_test_violation(
        content_scan=content_scan,
        pattern=patterns[0],
        violation_type=ViolationType.MEDICAL_DATA,
        severity=SensitivityLevel.HIGH,
        matched_content="INS-123456789",
        context_snippet="Insurance ID detected",
        is_resolved=False,
    )
    violations.append(medical_violation)

    return {
        "user": user,
        "patterns": patterns,
        "content_scan": content_scan,
        "violations": violations,
    }


def cleanup_test_data(user):
    """Clean up all test data for a user.

    Args:
        user: The user whose test data should be cleaned up
    """
    from analytics.models import PrivacyInsight

    # Delete insights
    PrivacyInsight.objects.filter(user=user).delete()

    # Delete violations and scans
    ContentScan.objects.filter(user=user).delete()
