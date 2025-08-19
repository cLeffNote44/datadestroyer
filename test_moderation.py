#!/usr/bin/env python
"""Quick test script for content moderation functionality"""

import os
import sys

import django

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "destroyer.settings")
django.setup()

from moderation.content_analyzer import analyze_content
from moderation.models import SensitiveContentPattern


def test_content_analysis():
    """Test the content analysis engine"""
    print("🔍 Testing Content Moderation System")
    print("=" * 50)

    # Test content with various PII types
    test_content = """
    Hi there! My name is John Smith and here's my information:

    SSN: 123-45-6789
    Credit Card: 4532-1234-5678-9012
    Phone: (555) 123-4567
    Email: john.smith@example.com
    Bank Account: 12345678901234567
    Medicare: 123-45-6789A

    Please keep this confidential!
    """

    print(f"📝 Analyzing content ({len(test_content)} characters)...")
    print()

    # Run analysis
    result = analyze_content(test_content, "medium")

    print(f"⏱️  Processing time: {result.processing_time_ms}ms")
    print(f"🚨 Violations found: {result.violations_found}")
    print(f"📊 Risk score: {result.scan_score}/100")
    print(f"⚠️  Highest severity: {result.highest_severity}")
    print(f"🎯 Total matches: {result.total_matches}")
    print()

    if result.detections:
        print("🔍 Detected violations:")
        for detection in result.detections:
            print(f"  • {detection.pattern_name} ({detection.sensitivity})")
            print(f"    Type: {detection.pattern_type}")
            print(f"    Matches: {detection.match_count}")
            print(f"    Found: {detection.matches[:2]}...")  # Show first 2 matches
            print()

    print("✅ Content analysis test completed!")

    # Show pattern count
    pattern_count = SensitiveContentPattern.objects.filter(is_active=True).count()
    print(f"📋 Active patterns loaded: {pattern_count}")


if __name__ == "__main__":
    test_content_analysis()
