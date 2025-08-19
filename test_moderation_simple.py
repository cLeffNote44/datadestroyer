#!/usr/bin/env python
"""
Simple test script to verify basic moderation API functionality.
"""

import os
import sys

import django

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "destroyer.settings")
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from moderation.models import SensitiveContentPattern, SensitivityLevel, ViolationType

User = get_user_model()


def setup_test_user():
    """Create a test user"""
    user, created = User.objects.get_or_create(
        username="test_user",
        defaults={"email": "test@example.com", "first_name": "Test", "last_name": "User"},
    )

    if created:
        user.set_password("testpass123")
        user.save()
        print(f"✅ Created test user: {user.username}")
    else:
        print(f"✅ Using existing test user: {user.username}")

    return user


def create_sample_patterns():
    """Create some sample patterns for testing"""
    patterns_data = [
        {
            "name": "SSN Pattern",
            "pattern_type": ViolationType.PII_DETECTED,
            "regex_pattern": r"\b\d{3}-\d{2}-\d{4}\b",
            "description": "Detects Social Security Numbers",
            "sensitivity_level": SensitivityLevel.HIGH,
        },
        {
            "name": "Email Pattern",
            "pattern_type": ViolationType.PII_DETECTED,
            "regex_pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "description": "Detects email addresses",
            "sensitivity_level": SensitivityLevel.MEDIUM,
        },
        {
            "name": "Credit Card Pattern",
            "pattern_type": ViolationType.FINANCIAL_DATA,
            "regex_pattern": r"\b4\d{3}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b",
            "description": "Detects Visa credit card numbers",
            "sensitivity_level": SensitivityLevel.CRITICAL,
        },
    ]

    created_count = 0
    for pattern_data in patterns_data:
        pattern, created = SensitiveContentPattern.objects.get_or_create(
            name=pattern_data["name"], defaults=pattern_data
        )
        if created:
            created_count += 1

    total_patterns = SensitiveContentPattern.objects.count()
    print(f"✅ Patterns ready: {created_count} new, {total_patterns} total")
    return total_patterns


def test_basic_api_endpoints():
    """Test basic API endpoint accessibility"""
    print("\n🧪 Testing API endpoints...")

    # Enable DEBUG for better error messages in tests and fix ALLOWED_HOSTS
    from django.conf import settings

    original_debug = settings.DEBUG
    original_allowed_hosts = settings.ALLOWED_HOSTS[:]
    settings.DEBUG = True
    settings.ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver", "*"]

    # Create test user and login
    user = setup_test_user()
    client = APIClient()
    client.force_authenticate(user=user)

    # Create sample patterns
    pattern_count = create_sample_patterns()
    if pattern_count == 0:
        print("❌ No patterns available - API tests may fail")
        return False

    # Test endpoints
    endpoints_to_test = [
        ("GET", "/api/moderation/dashboard/", "Dashboard"),
        ("GET", "/api/moderation/patterns/", "Patterns List"),
        ("GET", "/api/moderation/scans/", "Scans List"),
        ("GET", "/api/moderation/violations/", "Violations List"),
        ("GET", "/api/moderation/settings/my_settings/", "User Settings"),
    ]

    results = []

    for method, endpoint, name in endpoints_to_test:
        try:
            if method == "GET":
                response = client.get(endpoint)
            else:
                response = client.post(endpoint, {})

            if response.status_code in [200, 201]:
                print(f"✅ {name}: {response.status_code}")
                results.append(True)
            elif response.status_code == 404:
                print(f"⚠️ {name}: {response.status_code} (Not Found - check URL routing)")
                results.append(False)
            else:
                print(f"❌ {name}: {response.status_code}")
                results.append(False)

        except Exception as e:
            print(f"❌ {name}: Exception - {str(e)}")
            results.append(False)

    # Test content scanning
    print("\n🔍 Testing content scanning...")
    test_content = "My SSN is 123-45-6789 and email is test@example.com"
    scan_data = {"content": test_content, "scan_type": "manual"}

    try:
        response = client.post("/api/moderation/scan/", scan_data, format="json")
        if response.status_code in [200, 201]:
            result = response.json()
            print(f"✅ Content scan: {response.status_code}")
            print(f"   Violations found: {result.get('violations_found', 'N/A')}")
            print(f"   Risk level: {result.get('risk_level', 'N/A')}")
            results.append(True)
        else:
            print(f"❌ Content scan: {response.status_code}")
            if response.content:
                print(f"   Error: {response.content.decode()}")
            results.append(False)
    except Exception as e:
        print(f"❌ Content scan: Exception - {str(e)}")
        results.append(False)

    # Summary
    passed = sum(results)
    total = len(results)
    print(f"\n📊 Results: {passed}/{total} tests passed")

    return passed == total


if __name__ == "__main__":
    success = test_basic_api_endpoints()
    if success:
        print("\n🎉 All basic API tests passed!")
        sys.exit(0)
    else:
        print("\n⚠️ Some API tests failed - check configuration")
        sys.exit(1)
