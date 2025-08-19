"""
Test Suite for Data Discovery Classification Accuracy

This module provides comprehensive testing for classification accuracy across different data types,
testing both the classification engine and governance automation workflows.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, TransactionTestCase
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from datetime import datetime, timedelta
import json

from discovery.models import (
    DataAsset, ClassificationResult, ClassificationRule, DataDiscoveryInsight,
    RealTimeMonitor, MonitoringEvent
)
from discovery.classification_engine import DataClassificationEngine, ContentContext
from discovery.governance import GovernanceOrchestrator
from messaging.models import Message
from documents.models import Document


class ClassificationAccuracyTestCase(TestCase):
    """Test classification accuracy across different data types"""

    def setUp(self):
        """Set up test data and classification engine"""
        self.classification_engine = DataClassificationEngine()
        self.governance_orchestrator = GovernanceOrchestrator()
        
        # Create test data assets
        self.test_content_types = ContentType.objects.get_for_model(Message)
        self.test_asset = DataAsset.objects.create(
            name="Test Message Asset",
            content_type=self.test_content_types,
            object_id="123",
            location="database://messages/123",
            size_bytes=1024,
            is_active=True
        )
        
        # Define test datasets for different classification types
        self.test_datasets = {
            'PII': [
                "My name is John Smith and my email is john.smith@email.com",
                "SSN: 123-45-6789, Phone: (555) 123-4567",
                "Address: 123 Main St, Anytown, ST 12345",
                "Date of birth: 01/15/1985, Driver's license: DL123456789"
            ],
            'PHI': [
                "Patient John Doe, MRN: 123456, diagnosed with diabetes on 2023-01-15",
                "Blood pressure: 120/80, weight: 180lbs, temperature: 98.6°F",
                "Prescription: Metformin 500mg twice daily",
                "Insurance ID: BC123456789, Group: 001234"
            ],
            'FINANCIAL': [
                "Credit card: 4532-1234-5678-9012, CVV: 123, Exp: 12/25",
                "Bank account: 123456789, routing: 021000021",
                "Annual income: $75,000, Credit score: 720",
                "Investment account: INV123456, balance: $50,000"
            ],
            'CREDENTIALS': [
                "Username: admin, Password: P@ssw0rd123",
                "API key: sk-1234567890abcdef, Secret: abc123def456",
                "Database connection: user:password@localhost:5432/db",
                "SSH key: ssh-rsa AAAAB3NzaC1yc2EAAAADAQAB..."
            ],
            'INTELLECTUAL_PROPERTY': [
                "Patent application #US123456789 for revolutionary AI algorithm",
                "Trade secret formula: Component A + Component B + Catalyst C",
                "Proprietary source code for machine learning model",
                "Internal strategy document - CONFIDENTIAL - Q4 2023 roadmap"
            ],
            'PUBLIC': [
                "Welcome to our public website! Learn more about our services",
                "Company established in 1995, serving customers worldwide",
                "Contact us at info@company.com or visit our office",
                "Follow us on social media for latest updates"
            ]
        }

    def test_pii_classification_accuracy(self):
        """Test PII classification accuracy"""
        pii_content = self.test_datasets['PII']
        correct_classifications = 0
        
        for content in pii_content:
            context = ContentContext(
                content_type="messaging.message",
                model_name="message",
                app_name="messaging",
                size_bytes=len(content)
            )
            
            results = self.classification_engine.classify_content(content, context)
            
            # Check if PII was correctly identified
            pii_result = next((r for r in results if r.classification_type == 'PII'), None)
            if pii_result and pii_result.confidence_score >= 0.7:
                correct_classifications += 1
        
        accuracy = correct_classifications / len(pii_content)
        self.assertGreaterEqual(accuracy, 0.75, f"PII classification accuracy {accuracy:.2%} below threshold")

    def test_phi_classification_accuracy(self):
        """Test PHI classification accuracy"""
        phi_content = self.test_datasets['PHI']
        correct_classifications = 0
        
        for content in phi_content:
            context = ContentContext(
                content_type="messaging.message",
                model_name="message",
                app_name="messaging",
                size_bytes=len(content)
            )
            
            results = self.classification_engine.classify_content(content, context)
            
            # Check if PHI was correctly identified
            phi_result = next((r for r in results if r.classification_type == 'PHI'), None)
            if phi_result and phi_result.confidence_score >= 0.7:
                correct_classifications += 1
        
        accuracy = correct_classifications / len(phi_content)
        self.assertGreaterEqual(accuracy, 0.75, f"PHI classification accuracy {accuracy:.2%} below threshold")

    def test_financial_classification_accuracy(self):
        """Test financial data classification accuracy"""
        financial_content = self.test_datasets['FINANCIAL']
        correct_classifications = 0
        
        for content in financial_content:
            context = ContentContext(
                content_type="messaging.message",
                model_name="message",
                app_name="messaging",
                size_bytes=len(content)
            )
            
            results = self.classification_engine.classify_content(content, context)
            
            # Check if financial data was correctly identified
            financial_result = next((r for r in results if r.classification_type == 'FINANCIAL'), None)
            if financial_result and financial_result.confidence_score >= 0.7:
                correct_classifications += 1
        
        accuracy = correct_classifications / len(financial_content)
        self.assertGreaterEqual(accuracy, 0.75, f"Financial classification accuracy {accuracy:.2%} below threshold")

    def test_credentials_classification_accuracy(self):
        """Test credentials classification accuracy"""
        credentials_content = self.test_datasets['CREDENTIALS']
        correct_classifications = 0
        
        for content in credentials_content:
            context = ContentContext(
                content_type="messaging.message",
                model_name="message",
                app_name="messaging",
                size_bytes=len(content)
            )
            
            results = self.classification_engine.classify_content(content, context)
            
            # Check if credentials were correctly identified
            creds_result = next((r for r in results if r.classification_type == 'CREDENTIALS'), None)
            if creds_result and creds_result.confidence_score >= 0.7:
                correct_classifications += 1
        
        accuracy = correct_classifications / len(credentials_content)
        self.assertGreaterEqual(accuracy, 0.75, f"Credentials classification accuracy {accuracy:.2%} below threshold")

    def test_false_positive_rate(self):
        """Test false positive rate on public content"""
        public_content = self.test_datasets['PUBLIC']
        false_positives = 0
        
        for content in public_content:
            context = ContentContext(
                content_type="messaging.message",
                model_name="message",
                app_name="messaging",
                size_bytes=len(content)
            )
            
            results = self.classification_engine.classify_content(content, context)
            
            # Check for false positives (sensitive classifications on public content)
            sensitive_types = ['PII', 'PHI', 'FINANCIAL', 'CREDENTIALS']
            for result in results:
                if result.classification_type in sensitive_types and result.confidence_score >= 0.7:
                    false_positives += 1
                    break
        
        false_positive_rate = false_positives / len(public_content)
        self.assertLessEqual(false_positive_rate, 0.1, f"False positive rate {false_positive_rate:.2%} too high")

    def test_confidence_score_reliability(self):
        """Test that confidence scores are reliable and calibrated"""
        all_content = []
        expected_classifications = []
        
        # Prepare test data with expected classifications
        for classification_type, content_list in self.test_datasets.items():
            for content in content_list:
                all_content.append(content)
                expected_classifications.append(classification_type)
        
        high_confidence_correct = 0
        medium_confidence_correct = 0
        low_confidence_correct = 0
        
        high_confidence_total = 0
        medium_confidence_total = 0
        low_confidence_total = 0
        
        for content, expected_type in zip(all_content, expected_classifications):
            context = ContentContext(
                content_type="messaging.message",
                model_name="message",
                app_name="messaging",
                size_bytes=len(content)
            )
            
            results = self.classification_engine.classify_content(content, context)
            
            if results:
                best_result = max(results, key=lambda r: r.confidence_score)
                
                if best_result.confidence_score >= 0.8:
                    high_confidence_total += 1
                    if best_result.classification_type == expected_type:
                        high_confidence_correct += 1
                elif best_result.confidence_score >= 0.6:
                    medium_confidence_total += 1
                    if best_result.classification_type == expected_type:
                        medium_confidence_correct += 1
                else:
                    low_confidence_total += 1
                    if best_result.classification_type == expected_type:
                        low_confidence_correct += 1
        
        # High confidence should be highly accurate
        if high_confidence_total > 0:
            high_confidence_accuracy = high_confidence_correct / high_confidence_total
            self.assertGreaterEqual(high_confidence_accuracy, 0.9, 
                                  f"High confidence accuracy {high_confidence_accuracy:.2%} too low")
        
        # Medium confidence should be reasonably accurate
        if medium_confidence_total > 0:
            medium_confidence_accuracy = medium_confidence_correct / medium_confidence_total
            self.assertGreaterEqual(medium_confidence_accuracy, 0.7, 
                                  f"Medium confidence accuracy {medium_confidence_accuracy:.2%} too low")

    def test_classification_consistency(self):
        """Test that classification results are consistent across multiple runs"""
        test_content = self.test_datasets['PII'][0]  # Use first PII example
        
        context = ContentContext(
            content_type="messaging.message",
            model_name="message",
            app_name="messaging",
            size_bytes=len(test_content)
        )
        
        results_list = []
        for _ in range(5):  # Run classification 5 times
            results = self.classification_engine.classify_content(test_content, context)
            if results:
                best_result = max(results, key=lambda r: r.confidence_score)
                results_list.append((best_result.classification_type, best_result.confidence_score))
        
        # Check consistency
        if results_list:
            first_classification = results_list[0][0]
            consistent = all(result[0] == first_classification for result in results_list)
            self.assertTrue(consistent, "Classification results are not consistent across runs")
            
            # Check confidence score variance
            confidence_scores = [result[1] for result in results_list]
            if len(confidence_scores) > 1:
                variance = sum((score - sum(confidence_scores)/len(confidence_scores))**2 
                             for score in confidence_scores) / len(confidence_scores)
                self.assertLess(variance, 0.01, "Confidence scores vary too much across runs")

    def test_performance_benchmarks(self):
        """Test classification performance benchmarks"""
        import time
        
        test_content = self.test_datasets['PII'][0]
        context = ContentContext(
            content_type="messaging.message",
            model_name="message",
            app_name="messaging",
            size_bytes=len(test_content)
        )
        
        # Test single classification time
        start_time = time.time()
        results = self.classification_engine.classify_content(test_content, context)
        single_classification_time = time.time() - start_time
        
        self.assertLess(single_classification_time, 1.0, 
                       f"Single classification took {single_classification_time:.3f}s, too slow")
        
        # Test batch processing
        batch_content = list(self.test_datasets['PII'])
        start_time = time.time()
        
        for content in batch_content:
            self.classification_engine.classify_content(content, context)
        
        batch_time = time.time() - start_time
        avg_time_per_item = batch_time / len(batch_content)
        
        self.assertLess(avg_time_per_item, 0.5, 
                       f"Average batch processing time {avg_time_per_item:.3f}s per item, too slow")

    def test_governance_integration(self):
        """Test integration between classification and governance systems"""
        # Create a classification result
        classification_result = ClassificationResult.objects.create(
            data_asset=self.test_asset,
            classification_type='PII',
            confidence_score=0.85,
            rule_matches=['email_pattern', 'ssn_pattern'],
            metadata={'test': True}
        )
        
        # Apply governance
        governance_result = self.governance_orchestrator.process_classification_result(classification_result)
        
        # Verify governance was applied
        self.assertEqual(governance_result['status'], 'success')
        self.assertGreater(len(governance_result['governance_actions']), 0)
        
        # Check that asset was updated with governance metadata
        self.test_asset.refresh_from_db()
        self.assertIsNotNone(self.test_asset.metadata)
        self.assertIn('applied_policies', self.test_asset.metadata)
        self.assertIn('tags', self.test_asset.metadata)

    def test_edge_cases(self):
        """Test edge cases and error conditions"""
        # Test empty content
        results = self.classification_engine.classify_content("", ContentContext())
        self.assertEqual(len(results), 0)
        
        # Test very long content
        long_content = "This is sensitive data. " * 1000 + "SSN: 123-45-6789"
        context = ContentContext(
            content_type="messaging.message",
            model_name="message", 
            app_name="messaging",
            size_bytes=len(long_content)
        )
        
        results = self.classification_engine.classify_content(long_content, context)
        self.assertGreater(len(results), 0, "Failed to classify very long content")
        
        # Test special characters and Unicode
        unicode_content = "名前: John Smith, メール: john@email.com, SSN: 123-45-6789"
        results = self.classification_engine.classify_content(unicode_content, context)
        self.assertGreater(len(results), 0, "Failed to classify Unicode content")
        
        # Test mixed content types
        mixed_content = """
        Dear customer,
        
        Your account information:
        Name: Jane Doe
        SSN: 987-65-4321
        Credit Card: 4532-9876-5432-1098
        
        Medical Record:
        Patient ID: P123456
        Diagnosis: Hypertension
        
        Best regards,
        Customer Service
        """
        
        results = self.classification_engine.classify_content(mixed_content, context)
        
        # Should detect multiple classification types
        classification_types = [r.classification_type for r in results]
        self.assertIn('PII', classification_types)
        self.assertTrue(any(t in classification_types for t in ['FINANCIAL', 'PHI']))


class ClassificationRuleTestCase(TestCase):
    """Test custom classification rules"""

    def setUp(self):
        """Set up test classification rules"""
        self.classification_engine = DataClassificationEngine()
        
        # Create test rules
        self.email_rule = ClassificationRule.objects.create(
            name="Email Pattern",
            description="Detects email addresses",
            rule_type="regex",
            pattern=r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            classification_type="PII",
            confidence_weight=0.8,
            is_active=True
        )
        
        self.ssn_rule = ClassificationRule.objects.create(
            name="SSN Pattern",
            description="Detects Social Security Numbers",
            rule_type="regex", 
            pattern=r'\b\d{3}-\d{2}-\d{4}\b',
            classification_type="PII",
            confidence_weight=0.9,
            is_active=True
        )
        
        self.credit_card_rule = ClassificationRule.objects.create(
            name="Credit Card Pattern",
            description="Detects credit card numbers",
            rule_type="regex",
            pattern=r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            classification_type="FINANCIAL",
            confidence_weight=0.85,
            is_active=True
        )

    def test_regex_rule_matching(self):
        """Test regex pattern matching in rules"""
        test_content = "Contact me at john.doe@example.com or call (555) 123-4567"
        
        # Test email rule
        matches = self.classification_engine._apply_regex_rules([self.email_rule], test_content)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['rule_name'], "Email Pattern")
        self.assertIn("john.doe@example.com", matches[0]['matches'])

    def test_multiple_rule_matching(self):
        """Test content matching multiple rules"""
        test_content = "Customer: John Doe, Email: john@example.com, SSN: 123-45-6789"
        
        rules = [self.email_rule, self.ssn_rule]
        matches = self.classification_engine._apply_regex_rules(rules, test_content)
        
        self.assertEqual(len(matches), 2)
        rule_names = [match['rule_name'] for match in matches]
        self.assertIn("Email Pattern", rule_names)
        self.assertIn("SSN Pattern", rule_names)

    def test_rule_confidence_weighting(self):
        """Test that rule confidence weights are properly applied"""
        test_content = "SSN: 123-45-6789"  # High confidence pattern
        
        context = ContentContext(
            content_type="messaging.message",
            model_name="message",
            app_name="messaging",
            size_bytes=len(test_content)
        )
        
        results = self.classification_engine.classify_content(test_content, context)
        
        # Should have high confidence due to SSN rule weight
        pii_result = next((r for r in results if r.classification_type == 'PII'), None)
        self.assertIsNotNone(pii_result)
        self.assertGreaterEqual(pii_result.confidence_score, 0.8)

    def test_inactive_rules_ignored(self):
        """Test that inactive rules are not applied"""
        # Deactivate email rule
        self.email_rule.is_active = False
        self.email_rule.save()
        
        test_content = "Email me at john@example.com"
        context = ContentContext()
        
        results = self.classification_engine.classify_content(test_content, context)
        
        # Should not detect PII since email rule is inactive
        pii_results = [r for r in results if r.classification_type == 'PII']
        
        # If any PII detected, it shouldn't be from the email rule
        for result in pii_results:
            self.assertNotIn("Email Pattern", result.rule_matches)

    def test_rule_priority_ordering(self):
        """Test that rules with higher confidence weights take priority"""
        # Create conflicting rules with different weights
        low_weight_rule = ClassificationRule.objects.create(
            name="Generic Pattern",
            description="Generic pattern with low weight",
            rule_type="regex",
            pattern=r'\b\d{3}-\d{2}-\d{4}\b',  # Same as SSN pattern
            classification_type="PUBLIC",  # Different classification
            confidence_weight=0.3,
            is_active=True
        )
        
        test_content = "ID: 123-45-6789"
        context = ContentContext()
        
        results = self.classification_engine.classify_content(test_content, context)
        
        if results:
            # The result with highest confidence should be from the SSN rule (0.9 weight)
            best_result = max(results, key=lambda r: r.confidence_score)
            self.assertEqual(best_result.classification_type, "PII")
            self.assertIn("SSN Pattern", best_result.rule_matches)


class PerformanceTestCase(TestCase):
    """Test performance characteristics of the classification system"""

    def setUp(self):
        """Set up performance testing environment"""
        self.classification_engine = DataClassificationEngine()

    def test_large_content_processing(self):
        """Test processing of large content volumes"""
        import time
        
        # Generate large content with embedded sensitive data
        large_content = []
        for i in range(100):
            content = f"Document {i}: This contains email user{i}@example.com and SSN {i:03d}-{i:02d}-{i:04d}"
            large_content.append(content)
        
        start_time = time.time()
        
        context = ContentContext(
            content_type="documents.document",
            model_name="document",
            app_name="documents",
            size_bytes=1024 * 100  # Simulate 100KB
        )
        
        total_classifications = 0
        for content in large_content:
            results = self.classification_engine.classify_content(content, context)
            total_classifications += len(results)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should process 100 documents in reasonable time
        self.assertLess(processing_time, 30.0, f"Large content processing took {processing_time:.2f}s")
        self.assertGreater(total_classifications, 0, "No classifications found in large content")

    def test_concurrent_classification(self):
        """Test concurrent classification processing"""
        import threading
        import time
        
        test_content = [
            "Email: user1@example.com, SSN: 123-45-6789",
            "Credit card: 4532-1234-5678-9012, phone: (555) 123-4567",
            "Patient ID: P12345, diagnosis: diabetes, insurance: BC123456"
        ]
        
        results = {}
        errors = []
        
        def classify_content(content, thread_id):
            try:
                context = ContentContext(
                    content_type="messaging.message",
                    model_name="message",
                    app_name="messaging"
                )
                
                thread_results = self.classification_engine.classify_content(content, context)
                results[thread_id] = thread_results
            except Exception as e:
                errors.append(f"Thread {thread_id}: {str(e)}")
        
        # Launch multiple threads
        threads = []
        for i, content in enumerate(test_content):
            thread = threading.Thread(target=classify_content, args=(content, i))
            threads.append(thread)
        
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        
        # Check results
        self.assertEqual(len(errors), 0, f"Concurrent processing errors: {errors}")
        self.assertEqual(len(results), len(test_content), "Not all threads completed")
        
        # Should complete in reasonable time
        concurrent_time = end_time - start_time
        self.assertLess(concurrent_time, 10.0, f"Concurrent processing took {concurrent_time:.2f}s")

    def test_memory_usage(self):
        """Test memory usage during classification"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Process many documents
        context = ContentContext()
        
        for i in range(50):
            large_content = "This is a test document with sensitive data. " * 100
            large_content += f"Email: user{i}@example.com, SSN: {i:03d}-{i:02d}-{i:04d}"
            
            results = self.classification_engine.classify_content(large_content, context)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB)
        memory_increase_mb = memory_increase / 1024 / 1024
        self.assertLess(memory_increase_mb, 100, 
                       f"Memory usage increased by {memory_increase_mb:.2f}MB")


if __name__ == '__main__':
    unittest.main()
