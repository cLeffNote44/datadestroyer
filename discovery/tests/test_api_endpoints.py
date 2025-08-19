"""
API Testing Suite for Discovery System Endpoints

This module provides comprehensive API testing for all discovery system endpoints,
including dashboards, governance APIs, and real-time monitoring.
"""

import json
from unittest.mock import patch, Mock
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from discovery.models import (
    DataAsset, ClassificationResult, ClassificationRule, DataDiscoveryInsight,
    RealTimeMonitor, MonitoringEvent, DiscoveryJob, DataLineage
)
from messaging.models import Message
from documents.models import Document


class DiscoveryDashboardAPITestCase(APITestCase):
    """Test discovery dashboard API endpoints"""

    def setUp(self):
        """Set up test data for dashboard API testing"""
        # Create test user and authenticate
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

        # Create test data assets
        self.content_type = ContentType.objects.get_for_model(Message)
        
        self.assets = []
        for i in range(5):
            asset = DataAsset.objects.create(
                name=f"Test Asset {i}",
                content_type=self.content_type,
                object_id=str(i),
                location=f"database://messages/{i}",
                size_bytes=1024 * (i + 1),
                is_active=True,
                primary_classification='PII' if i % 2 == 0 else 'PUBLIC',
                sensitivity_level='high' if i % 2 == 0 else 'low'
            )
            self.assets.append(asset)

        # Create classification results
        for i, asset in enumerate(self.assets):
            ClassificationResult.objects.create(
                data_asset=asset,
                classification_type='PII' if i % 2 == 0 else 'PUBLIC',
                confidence_score=0.8 + (i * 0.05),
                rule_matches=['email_pattern'] if i % 2 == 0 else ['public_content'],
                metadata={'test': True}
            )

        # Create discovery jobs
        for i in range(3):
            DiscoveryJob.objects.create(
                name=f"Test Job {i}",
                description=f"Test discovery job {i}",
                job_type='full_scan',
                target_model='messaging.message',
                status='completed' if i < 2 else 'running',
                items_discovered=10 + i,
                items_classified=8 + i,
                started_at=timezone.now(),
                completed_at=timezone.now() if i < 2 else None
            )

        # Create real-time monitors
        self.monitor = RealTimeMonitor.objects.create(
            name="Test Monitor",
            description="Test monitoring setup",
            monitor_type='model_changes',
            target_specification={'apps': ['messaging']},
            auto_classify=True,
            alert_on_sensitive=True,
            is_active=True
        )

        # Create monitoring events
        for i in range(3):
            MonitoringEvent.objects.create(
                monitor=self.monitor,
                event_type='model_created',
                event_data={'test': i},
                triggered_alert=i == 0
            )

        # Create insights
        for i in range(2):
            DataDiscoveryInsight.objects.create(
                asset=self.assets[i],
                insight_type='security',
                title=f"Test Insight {i}",
                description=f"Test insight description {i}",
                severity='high' if i == 0 else 'medium',
                is_resolved=False
            )

    def test_discovery_dashboard_endpoint(self):
        """Test discovery dashboard API endpoint"""
        url = reverse('discovery:discovery-dashboard')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # Check response structure
        self.assertIn('summary', data)
        self.assertIn('classification_distribution', data)
        self.assertIn('sensitivity_distribution', data)
        self.assertIn('top_classifications', data)
        self.assertIn('system_health', data)

        # Verify summary data
        summary = data['summary']
        self.assertEqual(summary['total_assets'], 5)
        self.assertGreaterEqual(summary['discovery_jobs_7d'], 3)
        self.assertEqual(summary['active_monitors'], 1)

        # Verify classification distribution
        classification_dist = data['classification_distribution']
        self.assertIsInstance(classification_dist, dict)

        # Verify system health
        health = data['system_health']
        self.assertEqual(health['classification_engine_status'], 'active')

    def test_governance_dashboard_endpoint(self):
        """Test governance dashboard API endpoint"""
        # Add governance metadata to test assets
        self.assets[0].metadata = {
            'applied_policies': ['PII Protection'],
            'tags': ['sensitive', 'gdpr-scope'],
            'retention_date': '2025-01-01T00:00:00Z',
            'access_recommendations': {
                'priority': 'high',
                'recommendations': {'encryption_required': True}
            }
        }
        self.assets[0].save()

        url = reverse('discovery:governance-dashboard')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # Check response structure
        self.assertIn('governance_overview', data)
        self.assertIn('policy_distribution', data)
        self.assertIn('classification_governance', data)
        self.assertIn('access_control', data)
        self.assertIn('compliance', data)

        # Verify governance overview
        overview = data['governance_overview']
        self.assertEqual(overview['total_assets'], 5)
        self.assertGreaterEqual(overview['assets_with_governance'], 0)

        # Verify compliance data
        compliance = data['compliance']
        self.assertIn('overall_score', compliance)
        self.assertIn('compliant_assets', compliance)
        self.assertIn('non_compliant_assets', compliance)

    def test_governance_dashboard_with_framework_filter(self):
        """Test governance dashboard with framework filtering"""
        url = reverse('discovery:governance-dashboard')
        response = self.client.get(url, {'framework': 'GDPR'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # Should still have valid structure
        self.assertIn('governance_overview', data)
        self.assertIn('compliance', data)

    def test_dashboard_authentication_required(self):
        """Test that dashboard endpoints require authentication"""
        self.client.force_authenticate(user=None)
        
        url = reverse('discovery:discovery-dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        url = reverse('discovery:governance-dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_dashboard_performance(self):
        """Test dashboard API performance"""
        import time

        url = reverse('discovery:discovery-dashboard')
        
        start_time = time.time()
        response = self.client.get(url)
        end_time = time.time()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should respond within reasonable time
        response_time = end_time - start_time
        self.assertLess(response_time, 2.0, f"Dashboard response took {response_time:.3f}s")

    def test_dashboard_with_large_dataset(self):
        """Test dashboard performance with larger dataset"""
        # Create additional test data
        for i in range(100, 200):
            asset = DataAsset.objects.create(
                name=f"Large Dataset Asset {i}",
                content_type=self.content_type,
                object_id=str(i),
                location=f"database://messages/{i}",
                size_bytes=1024,
                is_active=True,
                primary_classification='PII' if i % 3 == 0 else 'PUBLIC'
            )

            ClassificationResult.objects.create(
                data_asset=asset,
                classification_type='PII' if i % 3 == 0 else 'PUBLIC',
                confidence_score=0.7,
                rule_matches=['test_pattern']
            )

        url = reverse('discovery:discovery-dashboard')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # Should handle larger dataset correctly
        self.assertGreaterEqual(data['summary']['total_assets'], 105)

    def test_dashboard_error_handling(self):
        """Test dashboard error handling"""
        # Mock a database error
        with patch('discovery.models.DataAsset.objects.filter') as mock_filter:
            mock_filter.side_effect = Exception("Database error")
            
            url = reverse('discovery:discovery-dashboard')
            response = self.client.get(url)
            
            # Should handle error gracefully (depends on implementation)
            # Either return 500 or fallback data
            self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR])


class APIEndpointIntegrationTestCase(APITestCase):
    """Integration tests for API endpoints with real data flows"""

    def setUp(self):
        """Set up integration test environment"""
        self.user = User.objects.create_user(
            username='integrationuser',
            email='integration@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

        # Create a full data discovery scenario
        self.content_type = ContentType.objects.get_for_model(Message)

    def test_full_discovery_workflow_api(self):
        """Test complete discovery workflow through API"""
        # 1. Create initial data asset
        asset = DataAsset.objects.create(
            name="Integration Test Asset",
            content_type=self.content_type,
            object_id="integration_test",
            location="database://messages/integration_test",
            size_bytes=2048,
            is_active=True
        )

        # 2. Create classification result
        classification = ClassificationResult.objects.create(
            data_asset=asset,
            classification_type='PII',
            confidence_score=0.9,
            rule_matches=['email_pattern', 'ssn_pattern'],
            metadata={'integration_test': True}
        )

        # 3. Create discovery job
        job = DiscoveryJob.objects.create(
            name="Integration Test Job",
            description="Testing full workflow",
            job_type='targeted_scan',
            target_model='messaging.message',
            status='completed',
            items_discovered=1,
            items_classified=1,
            started_at=timezone.now(),
            completed_at=timezone.now()
        )

        # 4. Check discovery dashboard reflects new data
        dashboard_url = reverse('discovery:discovery-dashboard')
        dashboard_response = self.client.get(dashboard_url)
        
        self.assertEqual(dashboard_response.status_code, status.HTTP_200_OK)
        dashboard_data = dashboard_response.json()
        
        self.assertGreaterEqual(dashboard_data['summary']['total_assets'], 1)
        self.assertGreaterEqual(dashboard_data['summary']['successful_jobs_7d'], 1)

        # 5. Check governance dashboard
        governance_url = reverse('discovery:governance-dashboard')
        governance_response = self.client.get(governance_url)
        
        self.assertEqual(governance_response.status_code, status.HTTP_200_OK)
        governance_data = governance_response.json()
        
        self.assertGreaterEqual(governance_data['governance_overview']['total_assets'], 1)

    def test_api_data_consistency(self):
        """Test data consistency across different API endpoints"""
        # Create test data
        assets = []
        for i in range(3):
            asset = DataAsset.objects.create(
                name=f"Consistency Test Asset {i}",
                content_type=self.content_type,
                object_id=f"consistency_{i}",
                location=f"database://messages/consistency_{i}",
                size_bytes=1024,
                is_active=True,
                primary_classification='PII'
            )
            assets.append(asset)

            ClassificationResult.objects.create(
                data_asset=asset,
                classification_type='PII',
                confidence_score=0.8,
                rule_matches=['test_pattern']
            )

        # Get data from discovery dashboard
        discovery_url = reverse('discovery:discovery-dashboard')
        discovery_response = self.client.get(discovery_url)
        discovery_data = discovery_response.json()

        # Get data from governance dashboard
        governance_url = reverse('discovery:governance-dashboard')
        governance_response = self.client.get(governance_url)
        governance_data = governance_response.json()

        # Verify consistency
        self.assertEqual(
            discovery_data['summary']['total_assets'],
            governance_data['governance_overview']['total_assets']
        )

        # Both should show same asset count
        self.assertGreaterEqual(discovery_data['summary']['total_assets'], 3)

    def test_api_response_format_consistency(self):
        """Test that API responses have consistent format"""
        endpoints = [
            reverse('discovery:discovery-dashboard'),
            reverse('discovery:governance-dashboard'),
        ]

        for endpoint in endpoints:
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            
            data = response.json()
            
            # All endpoints should return JSON
            self.assertIsInstance(data, dict)
            
            # Should have timestamp
            self.assertIn('timestamp', data)
            
            # Timestamp should be valid ISO format
            from datetime import datetime
            try:
                datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
            except ValueError:
                self.fail(f"Invalid timestamp format in {endpoint}")

    def test_concurrent_api_requests(self):
        """Test handling of concurrent API requests"""
        import threading
        import time

        results = {}
        errors = []

        def make_request(endpoint, request_id):
            try:
                response = self.client.get(endpoint)
                results[request_id] = {
                    'status_code': response.status_code,
                    'response_time': time.time()
                }
            except Exception as e:
                errors.append(f"Request {request_id}: {str(e)}")

        # Launch concurrent requests
        threads = []
        endpoint = reverse('discovery:discovery-dashboard')
        
        start_time = time.time()
        for i in range(5):
            thread = threading.Thread(target=make_request, args=(endpoint, i))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        end_time = time.time()

        # Check results
        self.assertEqual(len(errors), 0, f"Concurrent request errors: {errors}")
        self.assertEqual(len(results), 5, "Not all requests completed")
        
        # All requests should succeed
        for request_id, result in results.items():
            self.assertEqual(result['status_code'], status.HTTP_200_OK,
                           f"Request {request_id} failed")

        # Should handle concurrent requests efficiently
        total_time = end_time - start_time
        self.assertLess(total_time, 10.0, f"Concurrent requests took {total_time:.2f}s")


class APISecurityTestCase(APITestCase):
    """Test API security and authorization"""

    def setUp(self):
        """Set up security testing environment"""
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            is_staff=True,
            is_superuser=True
        )
        
        self.regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com', 
            password='regularpass123'
        )

    def test_unauthenticated_access_denied(self):
        """Test that unauthenticated requests are denied"""
        endpoints = [
            reverse('discovery:discovery-dashboard'),
            reverse('discovery:governance-dashboard'),
        ]

        for endpoint in endpoints:
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED,
                           f"Unauthenticated access allowed to {endpoint}")

    def test_authenticated_access_allowed(self):
        """Test that authenticated users can access endpoints"""
        self.client.force_authenticate(user=self.regular_user)
        
        endpoints = [
            reverse('discovery:discovery-dashboard'),
            reverse('discovery:governance-dashboard'),
        ]

        for endpoint in endpoints:
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, status.HTTP_200_OK,
                           f"Authenticated access denied to {endpoint}")

    def test_input_validation(self):
        """Test input validation on API endpoints"""
        self.client.force_authenticate(user=self.regular_user)
        
        # Test governance dashboard with invalid framework
        url = reverse('discovery:governance-dashboard')
        response = self.client.get(url, {'framework': 'INVALID_FRAMEWORK'})
        
        # Should either accept (and ignore) or return 400
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])

    def test_sql_injection_protection(self):
        """Test protection against SQL injection attempts"""
        self.client.force_authenticate(user=self.regular_user)
        
        # Test with SQL injection attempt in query parameters
        malicious_params = {
            'framework': "'; DROP TABLE discovery_dataasset; --",
            'filter': "1' OR '1'='1",
        }
        
        url = reverse('discovery:governance-dashboard')
        response = self.client.get(url, malicious_params)
        
        # Should not cause server error and should handle safely
        self.assertIn(response.status_code, [
            status.HTTP_200_OK, 
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ])

    def test_response_data_sanitization(self):
        """Test that response data doesn't contain sensitive information"""
        self.client.force_authenticate(user=self.regular_user)
        
        # Create asset with sensitive metadata
        content_type = ContentType.objects.get_for_model(Message)
        asset = DataAsset.objects.create(
            name="Sensitive Test Asset",
            content_type=content_type,
            object_id="sensitive_test",
            location="database://messages/sensitive_test",
            size_bytes=1024,
            is_active=True,
            metadata={
                'secret_key': 'super_secret_value',
                'password': 'hidden_password',
                'api_token': 'secret_token_123'
            }
        )

        url = reverse('discovery:discovery-dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response_text = response.content.decode()
        
        # Response should not contain sensitive values
        sensitive_values = ['super_secret_value', 'hidden_password', 'secret_token_123']
        for sensitive_value in sensitive_values:
            self.assertNotIn(sensitive_value, response_text,
                           f"Sensitive value '{sensitive_value}' exposed in API response")


class APILoadTestCase(APITestCase):
    """Load testing for API endpoints"""

    def setUp(self):
        """Set up load testing environment"""
        self.user = User.objects.create_user(
            username='loadtest',
            email='loadtest@example.com',
            password='loadtest123'
        )
        self.client.force_authenticate(user=self.user)

        # Create larger dataset for load testing
        content_type = ContentType.objects.get_for_model(Message)
        
        for i in range(50):
            asset = DataAsset.objects.create(
                name=f"Load Test Asset {i}",
                content_type=content_type,
                object_id=f"load_test_{i}",
                location=f"database://messages/load_test_{i}",
                size_bytes=1024 * (i + 1),
                is_active=True,
                primary_classification='PII' if i % 2 == 0 else 'PUBLIC'
            )

            ClassificationResult.objects.create(
                data_asset=asset,
                classification_type='PII' if i % 2 == 0 else 'PUBLIC',
                confidence_score=0.7 + (i % 3) * 0.1,
                rule_matches=['test_pattern']
            )

    def test_dashboard_load_performance(self):
        """Test dashboard performance under load"""
        import time

        response_times = []
        
        # Make multiple requests
        for i in range(10):
            start_time = time.time()
            
            url = reverse('discovery:discovery-dashboard')
            response = self.client.get(url)
            
            end_time = time.time()
            response_time = end_time - start_time
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            response_times.append(response_time)

        # Calculate statistics
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        
        # Performance assertions
        self.assertLess(avg_response_time, 2.0, 
                       f"Average response time {avg_response_time:.3f}s too high")
        self.assertLess(max_response_time, 5.0,
                       f"Max response time {max_response_time:.3f}s too high")

    def test_governance_dashboard_load_performance(self):
        """Test governance dashboard performance under load"""
        import time

        response_times = []
        
        # Make multiple requests with different parameters
        frameworks = [None, 'GDPR', 'HIPAA', 'PCI_DSS']
        
        for i in range(8):
            framework = frameworks[i % len(frameworks)]
            
            start_time = time.time()
            
            url = reverse('discovery:governance-dashboard')
            params = {'framework': framework} if framework else {}
            response = self.client.get(url, params)
            
            end_time = time.time()
            response_time = end_time - start_time
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            response_times.append(response_time)

        # Performance assertions
        avg_response_time = sum(response_times) / len(response_times)
        self.assertLess(avg_response_time, 3.0,
                       f"Governance dashboard avg response time {avg_response_time:.3f}s too high")


if __name__ == '__main__':
    import unittest
    unittest.main()
