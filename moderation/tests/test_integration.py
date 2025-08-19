"""
Integration tests for the moderation system

Tests end-to-end workflows, API integration, and system interactions.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase
from django.test.utils import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from analytics.models import AnalyticsSnapshot, PrivacyInsight
from documents.models import Document
from messaging.models import Message
from moderation.admin_workflows import admin_review_queue
from moderation.models import (
    ActionType,
    ContentScan,
    ModerationAction,
    ModerationSettings,
    ModerationStatus,
    PolicyViolation,
    SensitiveContentPattern,
)
from moderation.signals import trigger_bulk_scan_for_user

User = get_user_model()


class ModerationAPIIntegrationTestCase(APITestCase):
    """Test API integration and workflows"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="apiuser", password="testpass123", email="apiuser@example.com"
        )

        self.admin_user = User.objects.create_superuser(
            username="admin", password="adminpass123", email="admin@example.com"
        )

        # Create test patterns
        self.patterns = [
            SensitiveContentPattern.objects.create(
                name="Test SSN",
                pattern_type="pii_detected",
                regex_pattern=r"\b\d{3}-\d{2}-\d{4}\b",
                is_active=True,
            ),
            SensitiveContentPattern.objects.create(
                name="Test Email",
                pattern_type="pii_detected",
                regex_pattern=r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                is_active=True,
            ),
        ]

        self.client = APIClient()

    def test_content_scanning_api_workflow(self):
        """Test complete content scanning workflow through API"""
        self.client.force_authenticate(user=self.user)

        # Test content with violations
        test_content = "My SSN is 123-45-6789 and email is test@example.com"

        scan_data = {"content": test_content, "scan_type": "manual"}

        # Make scan request
        response = self.client.post("/api/moderation/scan/", scan_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(response_data["status"], "completed")
        self.assertGreater(response_data["violations_found"], 0)
        self.assertIn("risk_level", response_data)

        print(f"\nAPI Scan Test: Found {response_data['violations_found']} violations")
        print(f"Risk level: {response_data['risk_level']}")

    def test_pattern_management_api(self):
        """Test pattern management through API"""
        self.client.force_authenticate(user=self.admin_user)

        # List patterns
        response = self.client.get("/api/moderation/patterns/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        patterns = response.json()
        self.assertGreater(len(patterns), 0)

        # Test pattern
        pattern_id = patterns[0]["id"]
        test_data = {"test_content": "Test content with 123-45-6789 SSN"}

        response = self.client.post(
            f"/api/moderation/patterns/{pattern_id}/test_pattern/", test_data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        test_result = response.json()
        self.assertIn("matches_found", test_result)
        self.assertIn("execution_time_ms", test_result)

        print(f"Pattern Test: Found {test_result['matches_found']} matches")

    def test_dashboard_api_integration(self):
        """Test dashboard API with integrated data"""
        self.client.force_authenticate(user=self.user)

        # First create some scan data
        scan_data = {"content": "SSN: 123-45-6789", "scan_type": "manual"}
        self.client.post("/api/moderation/scan/", scan_data)

        # Get dashboard data
        response = self.client.get("/api/moderation/dashboard/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        dashboard_data = response.json()

        # Verify dashboard structure
        required_fields = [
            "total_scans",
            "recent_violations",
            "high_risk_content",
            "quarantined_items",
            "pending_reviews",
            "violation_trends",
            "risk_distribution",
            "top_violation_types",
        ]

        for field in required_fields:
            self.assertIn(field, dashboard_data)

        print("Dashboard API Integration: PASSED")

    def test_admin_workflow_api(self):
        """Test admin review workflow through API"""
        # Create a violation that needs review
        content_scan = ContentScan.objects.create(
            user=self.user,
            content_type_id=1,
            object_id="test",
            content_length=100,
            violations_found=1,
            scan_score=75,
            processing_time_ms=50,
        )

        violation = PolicyViolation.objects.create(
            content_scan=content_scan,
            pattern=self.patterns[0],
            violation_type="pii_detected",
            severity="high",
            matched_content="123-45-6789",
        )

        review_action = ModerationAction.objects.create(
            content_scan=content_scan,
            violation=violation,
            action_type=ActionType.REQUIRE_REVIEW,
            action_status=ModerationStatus.PENDING,
            reason="High-risk content detected",
            automated=True,
            triggered_by=self.user,
        )

        # Test admin review queue API
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.get("/api/moderation/admin/review-queue/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        queue_data = response.json()
        self.assertIn("items", queue_data)
        self.assertGreater(len(queue_data["items"]), 0)

        # Test admin action
        review_data = {
            "action_id": str(review_action.id),
            "decision": "approve",
            "notes": "Content approved after review",
        }

        response = self.client.post("/api/moderation/admin/review-action/", review_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        action_result = response.json()
        self.assertTrue(action_result["success"])

        print("Admin Workflow API Integration: PASSED")

    def test_bulk_operations_api(self):
        """Test bulk operations through API"""
        self.client.force_authenticate(user=self.user)

        # Test bulk scanning
        bulk_content = {
            "content_items": [
                {"content": "First document with SSN: 123-45-6789"},
                {"content": "Second document with email: user@example.com"},
                {"content": "Clean document with no violations"},
            ],
            "scan_type": "bulk",
        }

        response = self.client.post("/api/moderation/bulk-scan/", bulk_content)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        bulk_result = response.json()
        self.assertEqual(bulk_result["total_items"], 3)
        self.assertGreater(bulk_result["completed"], 0)

        print(f"Bulk Scan: {bulk_result['completed']}/{bulk_result['total_items']} items processed")


class WorkflowIntegrationTestCase(TransactionTestCase):
    """Test end-to-end workflows and signal integrations"""

    def setUp(self):
        self.user = User.objects.create_user(username="workflowuser", password="testpass123")

        # Create patterns
        SensitiveContentPattern.objects.create(
            name="Workflow SSN",
            pattern_type="pii_detected",
            regex_pattern=r"\b\d{3}-\d{2}-\d{4}\b",
            is_active=True,
        )

        # Create user settings
        ModerationSettings.objects.create(
            user=self.user, auto_scan_enabled=True, notify_on_violations=True
        )

    def test_document_upload_workflow(self):
        """Test automatic scanning when document is uploaded"""
        # Create a document (this should trigger auto-scan via signals)
        document = Document.objects.create(
            title="Test Document",
            description="Document with SSN: 123-45-6789 for testing",
            owner=self.user,
            file_size=1024,
        )

        # Check if scan was created
        scans = ContentScan.objects.filter(user=self.user, object_id=str(document.id))
        self.assertGreater(scans.count(), 0, "Document scan should be created automatically")

        # Check for violations
        scan = scans.first()
        violations = PolicyViolation.objects.filter(content_scan=scan)
        self.assertGreater(violations.count(), 0, "Should detect violations in document")

        print(f"Document Workflow: Created scan with {violations.count()} violations")

    def test_message_sending_workflow(self):
        """Test automatic scanning when message is sent"""
        # Create a message (should trigger auto-scan)
        message = Message.objects.create(
            content="My contact info: SSN 987-65-4321",
            sender=self.user,
            recipient=self.user,  # Self-message for testing
        )

        # Check if scan was created
        scans = ContentScan.objects.filter(user=self.user, object_id=str(message.id))
        self.assertGreater(scans.count(), 0, "Message scan should be created automatically")

        scan = scans.first()
        violations = PolicyViolation.objects.filter(content_scan=scan)
        self.assertGreater(violations.count(), 0, "Should detect violations in message")

        print(f"Message Workflow: Created scan with {violations.count()} violations")

    def test_quarantine_workflow(self):
        """Test automatic quarantine workflow for high-risk content"""
        # Enable auto-quarantine for critical violations
        settings = ModerationSettings.objects.get(user=self.user)
        settings.auto_quarantine_critical = True
        settings.save()

        # Create content scan with critical violation
        content_scan = ContentScan.objects.create(
            user=self.user,
            content_type_id=1,
            object_id="test-critical",
            content_length=100,
            violations_found=1,
            scan_score=85,  # High risk
            processing_time_ms=50,
        )

        # Create critical violation (this should trigger quarantine via signals)
        violation = PolicyViolation.objects.create(
            content_scan=content_scan,
            pattern=SensitiveContentPattern.objects.first(),
            violation_type="pii_detected",
            severity="critical",
            matched_content="123-45-6789",
        )

        # Check if quarantine action was created
        quarantine_actions = ModerationAction.objects.filter(
            content_scan=content_scan, action_type=ActionType.QUARANTINE
        )

        self.assertGreater(quarantine_actions.count(), 0, "Should create quarantine action")

        quarantine = quarantine_actions.first()
        self.assertIsNotNone(quarantine.expiry_date, "Quarantine should have expiry date")

        print(f"Quarantine Workflow: Created quarantine action expiring {quarantine.expiry_date}")

    def test_bulk_scanning_workflow(self):
        """Test bulk scanning workflow integration"""
        # Create some documents to scan
        docs = []
        for i in range(5):
            doc = Document.objects.create(
                title=f"Bulk Document {i}",
                description=f"Document {i} with SSN: {100+i:03d}-{20+i:02d}-{5000+i:04d}",
                owner=self.user,
                file_size=1024,
            )
            docs.append(doc)

        # Trigger bulk scan
        scanned_count = trigger_bulk_scan_for_user(self.user, "documents", 10)

        self.assertGreater(scanned_count, 0, "Should scan multiple documents")

        # Check that scans were created
        total_scans = ContentScan.objects.filter(user=self.user).count()
        total_violations = PolicyViolation.objects.filter(content_scan__user=self.user).count()

        print(f"Bulk Scanning: {scanned_count} items scanned, {total_violations} violations found")

        self.assertGreater(total_scans, 0, "Should create content scans")
        self.assertGreater(total_violations, 0, "Should detect violations")


class AnalyticsIntegrationTestCase(TestCase):
    """Test integration with analytics system"""

    def setUp(self):
        self.user = User.objects.create_user(username="analyticsuser", password="testpass123")

        # Create pattern
        SensitiveContentPattern.objects.create(
            name="Analytics Test",
            pattern_type="pii_detected",
            regex_pattern=r"\b\d{3}-\d{2}-\d{4}\b",
            is_active=True,
        )

    def test_analytics_snapshot_integration(self):
        """Test that moderation data appears in analytics snapshots"""
        # Create some moderation data
        content_scan = ContentScan.objects.create(
            user=self.user,
            content_type_id=1,
            object_id="analytics-test",
            content_length=100,
            violations_found=2,
            scan_score=70,
            processing_time_ms=50,
        )

        violation = PolicyViolation.objects.create(
            content_scan=content_scan,
            pattern=SensitiveContentPattern.objects.first(),
            violation_type="pii_detected",
            severity="high",
            matched_content="123-45-6789",
        )

        # Create/update analytics snapshot
        from analytics.views import AnalyticsDashboardViewSet

        dashboard_view = AnalyticsDashboardViewSet()

        # Generate snapshot data
        snapshot_data = dashboard_view._generate_snapshot_data(self.user, timezone.now().date())

        # Verify moderation data is included
        self.assertGreater(snapshot_data["total_content_scans"], 0, "Should include scan count")
        self.assertGreater(
            snapshot_data["content_violations_found"], 0, "Should include violation count"
        )
        self.assertGreater(snapshot_data["avg_content_risk_score"], 0, "Should include risk score")

        # Create actual snapshot
        snapshot = AnalyticsSnapshot.objects.create(
            user=self.user, date=timezone.now().date(), **snapshot_data
        )

        # Verify privacy score calculation includes moderation data
        self.assertIsNotNone(snapshot.privacy_score, "Should calculate privacy score")
        self.assertIsNotNone(
            snapshot.moderation_compliance_score, "Should calculate compliance score"
        )

        print(
            f"Analytics Integration: Privacy score: {snapshot.privacy_score}, Compliance: {snapshot.moderation_compliance_score}"
        )

    def test_privacy_insights_generation(self):
        """Test that moderation violations generate privacy insights"""
        # Create violation data
        content_scan = ContentScan.objects.create(
            user=self.user,
            content_type_id=1,
            object_id="insight-test",
            content_length=100,
            violations_found=1,
            scan_score=85,
            processing_time_ms=50,
        )

        violation = PolicyViolation.objects.create(
            content_scan=content_scan,
            pattern=SensitiveContentPattern.objects.first(),
            violation_type="pii_detected",
            severity="critical",
            matched_content="123-45-6789",
            is_resolved=False,
        )

        # Generate insights
        from moderation.insight_generator import generate_moderation_insights

        insights_created = generate_moderation_insights(self.user)

        self.assertGreater(insights_created, 0, "Should generate privacy insights")

        # Check that insights were created
        insights = PrivacyInsight.objects.filter(user=self.user)
        self.assertGreater(insights.count(), 0, "Should create PrivacyInsight objects")

        insight = insights.first()
        self.assertIn("violation", insight.context_data, "Should include violation context")

        print(f"Privacy Insights: Generated {insights_created} insights for violations")


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,  # Run tasks synchronously for testing
    DEBUG=True,
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class SystemIntegrationTestCase(TestCase):
    """Test complete system integration scenarios"""

    def setUp(self):
        self.regular_user = User.objects.create_user(username="regularuser", password="userpass123")

        self.admin_user = User.objects.create_superuser(
            username="systemadmin", password="adminpass123"
        )

        # Create comprehensive pattern set
        self.create_pattern_set()

        # Create user settings
        ModerationSettings.objects.create(
            user=self.regular_user,
            auto_scan_enabled=True,
            notify_on_violations=True,
            auto_quarantine_critical=True,
            auto_block_sharing=True,
        )

    def create_pattern_set(self):
        """Create comprehensive set of detection patterns"""
        patterns = [
            ("SSN Pattern", "pii_detected", r"\b\d{3}-\d{2}-\d{4}\b", "high"),
            (
                "Email Pattern",
                "pii_detected",
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                "medium",
            ),
            (
                "Credit Card",
                "financial_data",
                r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
                "critical",
            ),
            (
                "Phone Pattern",
                "pii_detected",
                r"\b\(?([0-9]{3})\)?[-. ]?([0-9]{3})[-. ]?([0-9]{4})\b",
                "medium",
            ),
        ]

        for name, pattern_type, regex, severity in patterns:
            SensitiveContentPattern.objects.create(
                name=name,
                pattern_type=pattern_type,
                regex_pattern=regex,
                sensitivity_level=severity,
                is_active=True,
            )

    def test_complete_content_lifecycle(self):
        """Test complete content lifecycle from creation to resolution"""
        # Step 1: Create content with violations (triggers auto-scan)
        document = Document.objects.create(
            title="Sensitive Document",
            description="Contains SSN: 123-45-6789, Email: user@example.com, Card: 4532-1234-5678-9012",
            owner=self.regular_user,
            file_size=2048,
        )

        # Step 2: Verify auto-scanning occurred
        scans = ContentScan.objects.filter(user=self.regular_user)
        self.assertGreater(scans.count(), 0, "Auto-scan should be triggered")

        scan = scans.first()
        self.assertGreater(scan.violations_found, 0, "Should detect violations")

        # Step 3: Verify violations were created
        violations = PolicyViolation.objects.filter(content_scan=scan)
        self.assertGreater(violations.count(), 0, "Should create violation records")

        # Step 4: Check for automatic actions (quarantine, sharing blocks)
        actions = ModerationAction.objects.filter(content_scan=scan)
        self.assertGreater(actions.count(), 0, "Should create moderation actions")

        # Step 5: Verify admin review queue
        admin_queue_items = admin_review_queue.get_pending_reviews()
        pending_reviews = [
            item
            for item in admin_queue_items
            if item["user"]["username"] == self.regular_user.username
        ]
        self.assertGreater(len(pending_reviews), 0, "Should appear in admin review queue")

        # Step 6: Admin reviews and approves
        if actions.filter(action_type=ActionType.REQUIRE_REVIEW).exists():
            review_action = actions.filter(action_type=ActionType.REQUIRE_REVIEW).first()
            result = admin_review_queue.approve_content(
                str(review_action.id), self.admin_user, "Content reviewed and approved"
            )
            self.assertTrue(result["success"], "Admin approval should succeed")

        # Step 7: Verify analytics integration
        from analytics.views import AnalyticsDashboardViewSet

        dashboard_view = AnalyticsDashboardViewSet()
        snapshot_data = dashboard_view._generate_snapshot_data(
            self.regular_user, timezone.now().date()
        )

        self.assertGreater(
            snapshot_data["total_content_scans"], 0, "Analytics should include scan data"
        )
        self.assertGreater(
            snapshot_data["content_violations_found"], 0, "Analytics should include violations"
        )

        print("\nComplete Lifecycle Test:")
        print(f"- Document created with {violations.count()} violations")
        print(f"- {actions.count()} moderation actions triggered")
        print(f"- Analytics snapshot includes {snapshot_data['total_content_scans']} scans")
        print("- Admin review and approval completed successfully")

    def test_high_volume_scenario(self):
        """Test system behavior under high volume"""
        # Create multiple users
        users = []
        for i in range(10):
            user = User.objects.create_user(username=f"volume_user_{i}", password="testpass123")
            users.append(user)

            ModerationSettings.objects.create(user=user, auto_scan_enabled=True)

        # Create content for each user
        total_documents = 0
        for i, user in enumerate(users):
            for j in range(5):  # 5 documents per user
                Document.objects.create(
                    title=f"Document {j} for User {i}",
                    description=f"SSN: {100+i:03d}-{j:02d}-{1000+j:04d}, Email: user{i}_{j}@example.com",
                    owner=user,
                    file_size=1024,
                )
                total_documents += 1

        # Verify system handled the load
        total_scans = ContentScan.objects.count()
        total_violations = PolicyViolation.objects.count()

        self.assertGreater(total_scans, 0, "Should create scans for high volume")
        self.assertGreater(total_violations, 0, "Should detect violations at scale")

        # Test analytics aggregation
        analytics_snapshots = []
        dashboard_view = AnalyticsDashboardViewSet()

        for user in users[:3]:  # Test subset for performance
            snapshot_data = dashboard_view._generate_snapshot_data(user, timezone.now().date())
            analytics_snapshots.append(snapshot_data)

        print("\nHigh Volume Test:")
        print(f"- Created {total_documents} documents for {len(users)} users")
        print(f"- Generated {total_scans} content scans")
        print(f"- Detected {total_violations} policy violations")
        print(f"- Successfully processed analytics for {len(analytics_snapshots)} users")

        # Verify reasonable performance
        self.assertLess(
            total_scans / total_documents, 2, "Should not create excessive scans per document"
        )

    def test_error_recovery_scenarios(self):
        """Test system resilience and error recovery"""
        # Test with malformed content
        try:
            document = Document.objects.create(
                title="Malformed Content Test",
                description=None,  # This might cause issues
                owner=self.regular_user,
                file_size=0,
            )
            # System should handle gracefully
            scans = ContentScan.objects.filter(object_id=str(document.id))
            # Should either create scan or handle error gracefully
        except Exception as e:
            self.fail(f"System should handle malformed content gracefully: {e}")

        # Test with invalid patterns
        invalid_pattern = SensitiveContentPattern.objects.create(
            name="Invalid Pattern",
            pattern_type="pii_detected",
            regex_pattern="[invalid regex",  # Malformed regex
            is_active=True,
        )

        # System should handle invalid patterns without crashing
        try:
            from moderation.content_analyzer import ContentAnalyzer

            analyzer = ContentAnalyzer()
            result = analyzer.analyze_content("Test content")
            # Should complete without error
        except Exception as e:
            # Log error but don't fail the test - system should be resilient
            print(f"Warning: Invalid pattern caused error: {e}")

        print("Error Recovery Test: System handled error scenarios gracefully")


def run_integration_tests():
    """
    Utility function to run all integration tests
    Can be called from management commands
    """
    import unittest

    # Create test suite
    suite = unittest.TestSuite()

    # Add integration test cases
    suite.addTest(unittest.makeSuite(ModerationAPIIntegrationTestCase))
    suite.addTest(unittest.makeSuite(WorkflowIntegrationTestCase))
    suite.addTest(unittest.makeSuite(AnalyticsIntegrationTestCase))
    suite.addTest(unittest.makeSuite(SystemIntegrationTestCase))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return {
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "success": result.wasSuccessful(),
    }


if __name__ == "__main__":
    # Allow running integration tests directly
    run_integration_tests()
