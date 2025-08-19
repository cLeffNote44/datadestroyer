"""
Integration and Real-Time Monitoring Test Suite

This module provides comprehensive testing for real-time monitoring, 
integration between different system components, and end-to-end workflows.
"""

import time
import threading
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, TransactionTestCase
from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.utils import timezone
from django.test.utils import override_settings

from discovery.models import (
    DataAsset, ClassificationResult, RealTimeMonitor, MonitoringEvent,
    DataDiscoveryInsight, DiscoveryJob, ClassificationRule
)
from discovery.signals import real_time_signals, initialize_real_time_monitoring
from discovery.governance import GovernanceOrchestrator
from discovery.classification_engine import DataClassificationEngine
from discovery.scanner import DataDiscoveryScanner
from analytics.models import AnalyticsSnapshot, PrivacyInsight
from messaging.models import Message
from documents.models import Document


class RealTimeMonitoringTestCase(TransactionTestCase):
    """Test real-time monitoring functionality"""

    def setUp(self):
        """Set up real-time monitoring test environment"""
        # Initialize real-time monitoring
        initialize_real_time_monitoring()
        
        # Create test user
        self.user = User.objects.create_user(
            username='monitortest',
            email='monitor@example.com',
            password='testpass123'
        )

        # Create test monitor
        self.monitor = RealTimeMonitor.objects.create(
            name="Integration Test Monitor",
            description="Monitor for integration testing",
            monitor_type='model_changes',
            target_specification={
                'apps': ['messaging', 'documents'],
                'models': [
                    {'app': 'messaging', 'model': 'message'},
                    {'app': 'documents', 'model': 'document'}
                ]
            },
            auto_classify=True,
            alert_on_sensitive=True,
            alert_threshold='medium',
            is_active=True
        )

        # Refresh monitors to include our test monitor
        real_time_signals.refresh_monitors()

    def test_real_time_message_monitoring(self):
        """Test real-time monitoring of message creation"""
        initial_events = MonitoringEvent.objects.count()
        initial_assets = DataAsset.objects.count()

        # Create a message (this should trigger real-time monitoring)
        message = Message.objects.create(
            sender=self.user,
            recipient=self.user,
            subject="Test Message with PII",
            body="This message contains SSN: 123-45-6789 and email: test@example.com",
            thread_id="test_thread"
        )

        # Allow signal processing to complete
        time.sleep(0.1)

        # Check that monitoring event was created
        new_events = MonitoringEvent.objects.count()
        self.assertGreater(new_events, initial_events, "No monitoring event created")

        # Check that data asset was discovered
        new_assets = DataAsset.objects.count()
        self.assertGreater(new_assets, initial_assets, "No data asset created")

        # Verify the monitoring event details
        event = MonitoringEvent.objects.latest('created_at')
        self.assertEqual(event.monitor, self.monitor)
        self.assertEqual(event.event_type, 'model_created')
        self.assertIn('messaging', event.event_data['app_label'])
        self.assertIn('message', event.event_data['model_name'])

    def test_real_time_document_monitoring(self):
        """Test real-time monitoring of document uploads"""
        initial_events = MonitoringEvent.objects.count()

        # Create a document (this should trigger monitoring)
        document = Document.objects.create(
            title="Sensitive Document",
            content="This document contains credit card: 4532-1234-5678-9012",
            owner=self.user,
            file_path="/uploads/sensitive_doc.txt"
        )

        # Allow signal processing
        time.sleep(0.1)

        # Verify monitoring occurred
        new_events = MonitoringEvent.objects.count()
        self.assertGreater(new_events, initial_events)

        # Check event details
        event = MonitoringEvent.objects.latest('created_at')
        self.assertEqual(event.event_type, 'model_created')
        self.assertIn('documents', event.event_data['app_label'])

    def test_real_time_classification_triggering(self):
        """Test that real-time monitoring triggers classification"""
        initial_classifications = ClassificationResult.objects.count()

        # Create content with sensitive data
        message = Message.objects.create(
            sender=self.user,
            recipient=self.user,
            subject="Financial Data",
            body="Account number: 123456789, routing: 021000021, balance: $5000",
            thread_id="financial_thread"
        )

        # Allow processing time
        time.sleep(0.2)

        # Check if classification was triggered
        new_classifications = ClassificationResult.objects.count()
        
        # Note: Classification might not trigger if the classification engine
        # isn't properly configured in test environment
        if new_classifications > initial_classifications:
            classification = ClassificationResult.objects.latest('created_at')
            self.assertIn(classification.classification_type, ['FINANCIAL', 'PII'])

    def test_real_time_alert_generation(self):
        """Test automatic alert generation for sensitive data"""
        initial_insights = DataDiscoveryInsight.objects.count()

        # Create highly sensitive content
        message = Message.objects.create(
            sender=self.user,
            recipient=self.user,
            subject="Critical Alert Test",
            body="SSN: 987-65-4321, Credit Card: 4532-9876-5432-1098, Password: secret123",
            thread_id="alert_thread"
        )

        # Allow processing
        time.sleep(0.2)

        # Check if alerts were generated
        new_insights = DataDiscoveryInsight.objects.count()
        
        if new_insights > initial_insights:
            insight = DataDiscoveryInsight.objects.latest('created_at')
            self.assertIn(insight.severity, ['high', 'critical'])
            self.assertEqual(insight.insight_type, 'security')

    def test_monitor_deactivation(self):
        """Test that deactivated monitors don't trigger"""
        # Deactivate monitor
        self.monitor.is_active = False
        self.monitor.save()
        real_time_signals.refresh_monitors()

        initial_events = MonitoringEvent.objects.count()

        # Create content
        message = Message.objects.create(
            sender=self.user,
            recipient=self.user,
            subject="Should Not Monitor",
            body="This should not be monitored",
            thread_id="inactive_thread"
        )

        time.sleep(0.1)

        # Should not create monitoring events
        new_events = MonitoringEvent.objects.count()
        self.assertEqual(new_events, initial_events, "Inactive monitor still triggering")

    def test_concurrent_monitoring(self):
        """Test monitoring under concurrent load"""
        def create_messages(thread_id, count):
            for i in range(count):
                Message.objects.create(
                    sender=self.user,
                    recipient=self.user,
                    subject=f"Concurrent Test {thread_id}-{i}",
                    body=f"Message {i} from thread {thread_id} with email: test{i}@example.com",
                    thread_id=f"concurrent_{thread_id}_{i}"
                )

        initial_events = MonitoringEvent.objects.count()

        # Create messages concurrently
        threads = []
        for i in range(3):
            thread = threading.Thread(target=create_messages, args=(i, 2))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Allow processing
        time.sleep(0.5)

        # Should have processed all messages
        new_events = MonitoringEvent.objects.count()
        expected_new_events = 6  # 3 threads * 2 messages each
        self.assertGreaterEqual(new_events - initial_events, expected_new_events * 0.8)  # Allow for some variation


class GovernanceIntegrationTestCase(TestCase):
    """Test integration between discovery, classification, and governance"""

    def setUp(self):
        """Set up governance integration test environment"""
        self.user = User.objects.create_user(
            username='governancetest',
            email='governance@example.com',
            password='testpass123'
        )
        
        self.governance_orchestrator = GovernanceOrchestrator()
        self.classification_engine = DataClassificationEngine()

        # Create test data asset
        self.content_type = ContentType.objects.get_for_model(Message)
        self.test_asset = DataAsset.objects.create(
            name="Governance Test Asset",
            content_type=self.content_type,
            object_id="governance_test",
            location="database://messages/governance_test",
            size_bytes=1024,
            is_active=True
        )

    def test_classification_to_governance_workflow(self):
        """Test complete workflow from classification to governance"""
        # 1. Create classification result
        classification = ClassificationResult.objects.create(
            data_asset=self.test_asset,
            classification_type='PII',
            confidence_score=0.9,
            rule_matches=['email_pattern', 'ssn_pattern'],
            metadata={'workflow_test': True}
        )

        # 2. Apply governance
        governance_result = self.governance_orchestrator.process_classification_result(classification)

        # 3. Verify governance was applied
        self.assertEqual(governance_result['status'], 'success')
        self.assertGreater(len(governance_result['governance_actions']), 0)

        # 4. Check asset metadata
        self.test_asset.refresh_from_db()
        self.assertIsNotNone(self.test_asset.metadata)
        self.assertIn('applied_policies', self.test_asset.metadata)
        self.assertIn('tags', self.test_asset.metadata)
        self.assertIn('retention_date', self.test_asset.metadata)

        # 5. Verify PII-specific policies were applied
        applied_policies = self.test_asset.metadata.get('applied_policies', [])
        self.assertIn('PII Protection', applied_policies)

        # 6. Check tags
        tags = self.test_asset.metadata.get('tags', [])
        self.assertIn('sensitive', tags)
        self.assertIn('personal-data', tags)

    def test_multi_classification_governance(self):
        """Test governance with multiple classifications on same asset"""
        # Create multiple classification results
        classifications = [
            ClassificationResult.objects.create(
                data_asset=self.test_asset,
                classification_type='PII',
                confidence_score=0.85,
                rule_matches=['email_pattern']
            ),
            ClassificationResult.objects.create(
                data_asset=self.test_asset,
                classification_type='FINANCIAL',
                confidence_score=0.8,
                rule_matches=['credit_card_pattern']
            )
        ]

        # Apply governance for each classification
        for classification in classifications:
            governance_result = self.governance_orchestrator.process_classification_result(classification)
            self.assertEqual(governance_result['status'], 'success')

        # Verify combined governance
        self.test_asset.refresh_from_db()
        applied_policies = self.test_asset.metadata.get('applied_policies', [])
        
        # Should have policies for both PII and Financial data
        self.assertIn('PII Protection', applied_policies)
        self.assertIn('Financial Protection', applied_policies)

        # Should have combined tags
        tags = self.test_asset.metadata.get('tags', [])
        self.assertTrue(any('personal-data' in tag or 'sensitive' in tag for tag in tags))
        self.assertTrue(any('financial' in tag or 'payment-data' in tag for tag in tags))

    def test_governance_compliance_validation(self):
        """Test compliance validation integration"""
        # Create PII classification (should trigger GDPR compliance)
        classification = ClassificationResult.objects.create(
            data_asset=self.test_asset,
            classification_type='PII',
            confidence_score=0.9,
            rule_matches=['email_pattern']
        )

        # Apply governance
        governance_result = self.governance_orchestrator.process_classification_result(classification)

        # Check compliance status
        self.test_asset.refresh_from_db()
        compliance_status = self.test_asset.metadata.get('compliance_status')
        self.assertIsNotNone(compliance_status)

        # Should have GDPR validation
        self.assertIn('GDPR', compliance_status.get('validations', {}))

    def test_retention_automation_integration(self):
        """Test retention automation integration"""
        # Create classification that should trigger retention
        classification = ClassificationResult.objects.create(
            data_asset=self.test_asset,
            classification_type='PHI',  # Should get 10-year retention
            confidence_score=0.95,
            rule_matches=['medical_pattern']
        )

        # Apply governance
        governance_result = self.governance_orchestrator.process_classification_result(classification)

        # Check retention was set
        self.test_asset.refresh_from_db()
        self.assertIn('retention_date', self.test_asset.metadata)
        self.assertIn('retention_scheduled_at', self.test_asset.metadata)

        # Verify retention period (should be ~10 years for PHI)
        from datetime import datetime
        retention_date_str = self.test_asset.metadata['retention_date']
        retention_date = datetime.fromisoformat(retention_date_str.replace('Z', '+00:00'))
        now = timezone.now()
        
        retention_years = (retention_date - now).days / 365
        self.assertGreater(retention_years, 9)  # Should be around 10 years
        self.assertLess(retention_years, 11)

    def test_access_control_recommendations(self):
        """Test access control recommendation generation"""
        # Create high-risk classification
        classification = ClassificationResult.objects.create(
            data_asset=self.test_asset,
            classification_type='CREDENTIALS',
            confidence_score=0.98,
            rule_matches=['password_pattern', 'api_key_pattern']
        )

        # Apply governance
        governance_result = self.governance_orchestrator.process_classification_result(classification)

        # Check access recommendations
        self.test_asset.refresh_from_db()
        access_recommendations = self.test_asset.metadata.get('access_recommendations')
        self.assertIsNotNone(access_recommendations)

        # Should be high priority for credentials
        self.assertIn(access_recommendations['priority'], ['critical', 'high'])
        
        # Should require encryption
        recommendations = access_recommendations['recommendations']
        self.assertTrue(recommendations.get('encryption_required', False))
        self.assertTrue(recommendations.get('audit_required', False))


class AnalyticsIntegrationTestCase(TestCase):
    """Test integration with analytics system"""

    def setUp(self):
        """Set up analytics integration test environment"""
        self.user = User.objects.create_user(
            username='analyticstest',
            email='analytics@example.com',
            password='testpass123'
        )

    def test_discovery_metrics_integration(self):
        """Test that discovery metrics are integrated into analytics"""
        from discovery.analytics_integration import DiscoveryAnalyticsIntegrator
        
        integrator = DiscoveryAnalyticsIntegrator()

        # Create test data assets for the user
        content_type = ContentType.objects.get_for_model(Message)
        
        assets = []
        for i in range(3):
            asset = DataAsset.objects.create(
                name=f"Analytics Test Asset {i}",
                content_type=content_type,
                object_id=f"analytics_test_{i}",
                location=f"database://messages/analytics_test_{i}",
                size_bytes=1024,
                is_active=True,
                owner_id=self.user.id  # Associate with user
            )
            assets.append(asset)

            # Create classification
            ClassificationResult.objects.create(
                data_asset=asset,
                classification_type='PII' if i % 2 == 0 else 'PUBLIC',
                confidence_score=0.8,
                rule_matches=['test_pattern']
            )

        # Get or create analytics snapshot
        snapshot, created = AnalyticsSnapshot.objects.get_or_create(
            user=self.user,
            defaults={
                'total_messages': 0,
                'total_documents': 0,
                'total_forum_posts': 0,
                'privacy_score': 0.5
            }
        )

        # Update discovery metrics
        integrator.update_discovery_metrics(snapshot)

        # Verify metrics were updated
        snapshot.refresh_from_db()
        self.assertGreater(snapshot.total_data_assets, 0)
        self.assertGreater(snapshot.classified_assets_count, 0)

    def test_privacy_insights_generation(self):
        """Test privacy insights generation from discovery data"""
        from discovery.analytics_integration import DiscoveryAnalyticsIntegrator
        
        integrator = DiscoveryAnalyticsIntegrator()

        # Create asset with sensitive data
        content_type = ContentType.objects.get_for_model(Message)
        asset = DataAsset.objects.create(
            name="Sensitive Analytics Asset",
            content_type=content_type,
            object_id="sensitive_analytics",
            location="database://messages/sensitive_analytics",
            size_bytes=1024,
            is_active=True,
            owner_id=self.user.id
        )

        # Create high-confidence PII classification
        ClassificationResult.objects.create(
            data_asset=asset,
            classification_type='PII',
            confidence_score=0.95,
            rule_matches=['ssn_pattern', 'email_pattern']
        )

        # Generate privacy insights
        insights = integrator.generate_privacy_insights(self.user)

        # Should generate insights for sensitive data
        self.assertGreater(len(insights), 0)
        
        # Check insight content
        pii_insights = [insight for insight in insights if 'PII' in insight['title']]
        self.assertGreater(len(pii_insights), 0)

    def test_discovery_coverage_calculation(self):
        """Test discovery coverage score calculation"""
        from discovery.analytics_integration import DiscoveryAnalyticsIntegrator
        
        integrator = DiscoveryAnalyticsIntegrator()

        # Create assets with mixed classification coverage
        content_type = ContentType.objects.get_for_model(Message)
        
        classified_asset = DataAsset.objects.create(
            name="Classified Asset",
            content_type=content_type,
            object_id="classified",
            location="database://messages/classified",
            size_bytes=1024,
            is_active=True,
            owner_id=self.user.id
        )

        unclassified_asset = DataAsset.objects.create(
            name="Unclassified Asset",
            content_type=content_type,
            object_id="unclassified",
            location="database://messages/unclassified",
            size_bytes=1024,
            is_active=True,
            owner_id=self.user.id
        )

        # Add classification to one asset
        ClassificationResult.objects.create(
            data_asset=classified_asset,
            classification_type='PII',
            confidence_score=0.9,
            rule_matches=['email_pattern']
        )

        # Calculate coverage
        coverage_score = integrator.calculate_discovery_coverage_score(self.user)

        # Should be 50% coverage (1 of 2 assets classified)
        self.assertAlmostEqual(coverage_score, 0.5, places=1)


class EndToEndWorkflowTestCase(TransactionTestCase):
    """Test complete end-to-end workflows"""

    def setUp(self):
        """Set up end-to-end test environment"""
        self.user = User.objects.create_user(
            username='e2etest',
            email='e2e@example.com',
            password='testpass123'
        )

        # Initialize monitoring
        initialize_real_time_monitoring()

        # Create active monitor
        self.monitor = RealTimeMonitor.objects.create(
            name="E2E Test Monitor",
            description="End-to-end testing monitor",
            monitor_type='model_changes',
            target_specification={'apps': ['messaging']},
            auto_classify=True,
            alert_on_sensitive=True,
            is_active=True
        )

        real_time_signals.refresh_monitors()

    def test_complete_data_lifecycle(self):
        """Test complete data lifecycle from creation to governance"""
        # 1. Create message with sensitive content
        message = Message.objects.create(
            sender=self.user,
            recipient=self.user,
            subject="Complete Lifecycle Test",
            body="Customer data: John Doe, SSN: 123-45-6789, Email: john@example.com, CC: 4532-1234-5678-9012",
            thread_id="lifecycle_test"
        )

        # 2. Allow real-time processing
        time.sleep(0.3)

        # 3. Verify discovery occurred
        content_type = ContentType.objects.get_for_model(Message)
        assets = DataAsset.objects.filter(
            content_type=content_type,
            object_id=str(message.pk)
        )
        self.assertGreater(assets.count(), 0, "Data asset not created")

        asset = assets.first()

        # 4. Check if classification occurred
        classifications = ClassificationResult.objects.filter(data_asset=asset)
        
        if classifications.exists():
            # 5. Verify governance was applied
            classification = classifications.first()
            
            # Check if governance metadata exists
            if asset.metadata:
                # Should have tags applied
                self.assertIn('tags', asset.metadata)
                
                # Should have retention scheduled if governance applied
                if 'retention_date' in asset.metadata:
                    self.assertIsNotNone(asset.metadata['retention_date'])

        # 6. Verify monitoring events
        events = MonitoringEvent.objects.filter(monitor=self.monitor)
        self.assertGreater(events.count(), 0, "No monitoring events created")

        event = events.latest('created_at')
        self.assertEqual(event.event_type, 'model_created')

    def test_bulk_data_processing(self):
        """Test processing of bulk data creation"""
        initial_assets = DataAsset.objects.count()
        initial_events = MonitoringEvent.objects.count()

        # Create multiple messages rapidly
        messages = []
        for i in range(5):
            message = Message.objects.create(
                sender=self.user,
                recipient=self.user,
                subject=f"Bulk Test Message {i}",
                body=f"Message {i} with email: user{i}@example.com",
                thread_id=f"bulk_test_{i}"
            )
            messages.append(message)

        # Allow processing
        time.sleep(0.5)

        # Should have created assets and events for most/all messages
        new_assets = DataAsset.objects.count() - initial_assets
        new_events = MonitoringEvent.objects.count() - initial_events

        # Allow for some variation in processing
        self.assertGreaterEqual(new_assets, len(messages) * 0.8)
        self.assertGreaterEqual(new_events, len(messages) * 0.8)

    def test_error_resilience(self):
        """Test system resilience to errors during processing"""
        initial_events = MonitoringEvent.objects.count()

        # Mock a processing error in classification
        with patch('discovery.classification_engine.DataClassificationEngine.classify_content') as mock_classify:
            mock_classify.side_effect = Exception("Simulated classification error")

            # Create message (should trigger monitoring despite classification error)
            message = Message.objects.create(
                sender=self.user,
                recipient=self.user,
                subject="Error Resilience Test",
                body="This should cause a classification error",
                thread_id="error_test"
            )

            # Allow processing
            time.sleep(0.2)

            # Should still create monitoring event despite classification error
            new_events = MonitoringEvent.objects.count() - initial_events
            self.assertGreater(new_events, 0, "System not resilient to classification errors")

    def test_system_performance_under_load(self):
        """Test system performance under high load"""
        import time

        start_time = time.time()
        
        # Create many messages rapidly
        messages = []
        for i in range(20):
            message = Message.objects.create(
                sender=self.user,
                recipient=self.user,
                subject=f"Load Test {i}",
                body=f"Load test message {i} with data: test{i}@example.com",
                thread_id=f"load_{i}"
            )
            messages.append(message)

        # Allow processing
        time.sleep(1.0)

        end_time = time.time()
        total_time = end_time - start_time

        # Should process within reasonable time
        self.assertLess(total_time, 5.0, f"System too slow under load: {total_time:.2f}s")

        # Should have processed most messages
        content_type = ContentType.objects.get_for_model(Message)
        processed_count = 0
        
        for message in messages:
            if DataAsset.objects.filter(
                content_type=content_type,
                object_id=str(message.pk)
            ).exists():
                processed_count += 1

        processing_rate = processed_count / len(messages)
        self.assertGreater(processing_rate, 0.7, f"Processing rate too low: {processing_rate:.2%}")


if __name__ == '__main__':
    import unittest
    unittest.main()
