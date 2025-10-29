#!/usr/bin/env python
"""
Test script for the moderation insight generator.

This script creates test violations and validates that appropriate
privacy insights are generated.
"""

import os
import sys

import django

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "destroyer.settings")
django.setup()

from django.contrib.auth import get_user_model

from analytics.models import PrivacyInsight
from moderation.insight_generator import ModerationInsightGenerator, generate_moderation_insights
from moderation.models import (
    ContentScan,
    ModerationStatus,
    PolicyViolation,
    SensitiveContentPattern,
    SeverityLevel,
    ViolationType,
)

User = get_user_model()


def create_test_user():
    """Create or get a test user"""
    user, created = User.objects.get_or_create(
        username="test_insights",
        defaults={"email": "test@example.com", "first_name": "Test", "last_name": "User"},
    )
    if created:
        print(f"✓ Created test user: {user.username}")
    else:
        print(f"✓ Using existing test user: {user.username}")

    return user


def create_test_violations(user):
    """Create test violations for the user"""

    # Get some patterns to use for violations
    patterns = list(SensitiveContentPattern.objects.filter(is_active=True)[:5])
    if not patterns:
        print("❌ No active patterns found. Run 'python manage.py load_builtin_patterns' first.")
        return []

    violations = []

    # Create a content scan
    content_scan = ContentScan.objects.create(
        user=user,
        content_text="Test content with SSN 123-45-6789 and credit card 4532 1234 5678 9012",
        scan_score=95.0,
        status=ModerationStatus.FLAGGED,
        scan_metadata={"test": True},
    )
    print(f"✓ Created content scan: {content_scan.id}")

    # Create multiple PII violations
    for i, pattern in enumerate(patterns[:3]):
        violation = PolicyViolation.objects.create(
            content_scan=content_scan,
            pattern=pattern,
            violation_type=ViolationType.PII_DETECTED,
            severity=SeverityLevel.HIGH,
            matched_text=f"test-data-{i}",
            context="Test violation context",
            confidence_score=0.95,
            is_resolved=False,
        )
        violations.append(violation)

    # Create a financial violation
    financial_pattern = patterns[0]  # Use any pattern for test
    financial_violation = PolicyViolation.objects.create(
        content_scan=content_scan,
        pattern=financial_pattern,
        violation_type=ViolationType.FINANCIAL_DATA,
        severity=SeverityLevel.CRITICAL,
        matched_text="4532-1234-5678-9012",
        context="Credit card number detected",
        confidence_score=0.98,
        is_resolved=False,
    )
    violations.append(financial_violation)

    # Create a medical violation
    medical_violation = PolicyViolation.objects.create(
        content_scan=content_scan,
        pattern=financial_pattern,  # Using any pattern for test
        violation_type=ViolationType.MEDICAL_DATA,
        severity=SeverityLevel.HIGH,
        matched_text="INS-123456789",
        context="Insurance ID detected",
        confidence_score=0.90,
        is_resolved=False,
    )
    violations.append(medical_violation)

    print(f"✓ Created {len(violations)} test violations")
    return violations


def test_insight_generation(user):
    """Test the insight generation for the user"""

    print("\n🔍 Testing insight generation...")

    # Generate insights using the class directly
    generator = ModerationInsightGenerator()
    insights = generator.generate_insights_for_user(user)

    print(f"✓ Generated {len(insights)} insights:")
    for insight in insights:
        print(f"   - {insight.title} ({insight.severity}) - {insight.insight_type}")
        print(f"     {insight.description[:100]}...")

    # Test the main function that saves insights
    print("\n💾 Testing insight saving...")
    initial_count = PrivacyInsight.objects.filter(user=user).count()
    insights_created = generate_moderation_insights(user)
    final_count = PrivacyInsight.objects.filter(user=user).count()

    print(f"✓ Created {insights_created} new insights")
    print(f"✓ Total insights for user: {final_count} (was {initial_count})")

    # Show the actual saved insights
    saved_insights = PrivacyInsight.objects.filter(user=user, is_dismissed=False).order_by(
        "-created_at"
    )
    print("\n📋 Saved insights in database:")
    for insight in saved_insights:
        print(f"   - {insight.title} ({insight.severity})")
        print(f"     Action: {insight.action_text}")
        if insight.action_url:
            print(f"     URL: {insight.action_url}")

    return insights_created > 0


def cleanup_test_data(user):
    """Clean up test data"""
    print("\n🧹 Cleaning up test data...")

    # Delete insights
    insights_deleted = PrivacyInsight.objects.filter(user=user).delete()[0]
    print(f"✓ Deleted {insights_deleted} insights")

    # Delete violations and scans
    scans_deleted = ContentScan.objects.filter(user=user).delete()[0]
    print(f"✓ Deleted {scans_deleted} content scans (and related violations)")

    # Delete test user
    user.delete()
    print(f"✓ Deleted test user: {user.username}")


def main():
    """Main test function"""
    print("🧪 Testing Moderation Insight Generator")
    print("=" * 50)

    try:
        # Create test data
        user = create_test_user()
        violations = create_test_violations(user)

        if not violations:
            print("❌ Could not create test violations. Exiting.")
            return False

        # Test insight generation
        success = test_insight_generation(user)

        if success:
            print("\n✅ All tests passed! The insight generator is working correctly.")
        else:
            print("\n❌ Tests failed. Please check the implementation.")

        # Ask if user wants to keep or clean up test data
        response = input("\nDo you want to keep the test data for inspection? (y/N): ")
        if response.lower() != "y":
            cleanup_test_data(user)
        else:
            print(f"\n📝 Test data preserved. User: {user.username}")
            print("   You can inspect the data in Django admin or with:")
            print(
                f"   python manage.py shell -c \"from django.contrib.auth import get_user_model; from analytics.models import PrivacyInsight; user = get_user_model().objects.get(username='{user.username}'); print(list(PrivacyInsight.objects.filter(user=user).values('title', 'severity')))\""
            )

        return success

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
