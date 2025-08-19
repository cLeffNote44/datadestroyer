"""
Test Runner and Configuration for Discovery System

This module provides test runner configuration, test utilities, and 
comprehensive test execution management for the discovery system.
"""

import os
import sys
import time
import psutil
from io import StringIO
from unittest import TextTestRunner, TestSuite
from django.test.runner import DiscoverRunner
from django.test.utils import setup_test_environment, teardown_test_environment
from django.db import connections
from django.core.management import call_command
from django.conf import settings


class DiscoveryTestRunner(DiscoverRunner):
    """Custom test runner for discovery system tests"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.test_results = {}
        self.performance_metrics = {}
        self.start_time = None
        self.memory_before = None
        
    def setup_test_environment(self, **kwargs):
        """Set up test environment with performance monitoring"""
        super().setup_test_environment(**kwargs)
        
        # Record initial memory usage
        process = psutil.Process()
        self.memory_before = process.memory_info().rss
        self.start_time = time.time()
        
        # Ensure test database is clean
        self._ensure_clean_test_db()
        
        # Initialize discovery system for testing
        self._initialize_discovery_system()
        
    def teardown_test_environment(self, **kwargs):
        """Clean up test environment and report metrics"""
        super().teardown_test_environment(**kwargs)
        
        # Calculate performance metrics
        if self.start_time:
            total_time = time.time() - self.start_time
            self.performance_metrics['total_execution_time'] = total_time
            
        if self.memory_before:
            process = psutil.Process()
            memory_after = process.memory_info().rss
            memory_increase = memory_after - self.memory_before
            self.performance_metrics['memory_increase_mb'] = memory_increase / 1024 / 1024
            
        # Report metrics
        self._report_test_metrics()
        
    def _ensure_clean_test_db(self):
        """Ensure test database starts clean"""
        from django.core.management import call_command
        
        # Flush the database
        call_command('flush', verbosity=0, interactive=False)
        
    def _initialize_discovery_system(self):
        """Initialize discovery system components for testing"""
        try:
            # Initialize real-time monitoring
            from discovery.signals import initialize_real_time_monitoring
            initialize_real_time_monitoring()
            
            # Create test classification rules
            self._create_test_classification_rules()
            
        except Exception as e:
            print(f"Warning: Could not fully initialize discovery system: {e}")
            
    def _create_test_classification_rules(self):
        """Create basic classification rules for testing"""
        from discovery.models import ClassificationRule
        
        # Email pattern rule
        ClassificationRule.objects.get_or_create(
            name="Test Email Pattern",
            defaults={
                'description': "Test email detection rule",
                'rule_type': 'regex',
                'pattern': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                'classification_type': 'PII',
                'confidence_weight': 0.8,
                'is_active': True
            }
        )
        
        # SSN pattern rule
        ClassificationRule.objects.get_or_create(
            name="Test SSN Pattern",
            defaults={
                'description': "Test SSN detection rule",
                'rule_type': 'regex',
                'pattern': r'\b\d{3}-\d{2}-\d{4}\b',
                'classification_type': 'PII',
                'confidence_weight': 0.9,
                'is_active': True
            }
        )
        
        # Credit card pattern rule
        ClassificationRule.objects.get_or_create(
            name="Test Credit Card Pattern",
            defaults={
                'description': "Test credit card detection rule",
                'rule_type': 'regex',
                'pattern': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
                'classification_type': 'FINANCIAL',
                'confidence_weight': 0.85,
                'is_active': True
            }
        )
        
    def _report_test_metrics(self):
        """Report test execution metrics"""
        print("\n" + "="*60)
        print("DISCOVERY SYSTEM TEST METRICS")
        print("="*60)
        
        if 'total_execution_time' in self.performance_metrics:
            exec_time = self.performance_metrics['total_execution_time']
            print(f"Total execution time: {exec_time:.2f} seconds")
            
        if 'memory_increase_mb' in self.performance_metrics:
            memory_inc = self.performance_metrics['memory_increase_mb']
            print(f"Memory increase: {memory_inc:.2f} MB")
            
        # Report test results summary
        if hasattr(self, 'suite'):
            print(f"Tests run: {self.suite.countTestCases()}")
            
        print("="*60)


class TestUtilities:
    """Utility functions for discovery system testing"""
    
    @staticmethod
    def create_test_user(username='testuser', email='test@example.com'):
        """Create a test user for testing"""
        from django.contrib.auth.models import User
        
        return User.objects.create_user(
            username=username,
            email=email,
            password='testpass123'
        )
    
    @staticmethod
    def create_test_data_asset(user=None, classification_type='PII'):
        """Create a test data asset"""
        from django.contrib.contenttypes.models import ContentType
        from discovery.models import DataAsset, ClassificationResult
        from messaging.models import Message
        
        if not user:
            user = TestUtilities.create_test_user()
            
        # Create test content
        content_type = ContentType.objects.get_for_model(Message)
        
        asset = DataAsset.objects.create(
            name="Test Asset",
            content_type=content_type,
            object_id="test_object",
            location="database://test/test_object",
            size_bytes=1024,
            is_active=True
        )
        
        # Create classification
        ClassificationResult.objects.create(
            data_asset=asset,
            classification_type=classification_type,
            confidence_score=0.85,
            rule_matches=['test_pattern'],
            metadata={'test': True}
        )
        
        return asset
    
    @staticmethod
    def create_test_monitor(name='Test Monitor'):
        """Create a test real-time monitor"""
        from discovery.models import RealTimeMonitor
        
        return RealTimeMonitor.objects.create(
            name=name,
            description="Test monitoring configuration",
            monitor_type='model_changes',
            target_specification={'apps': ['messaging']},
            auto_classify=True,
            alert_on_sensitive=True,
            is_active=True
        )
    
    @staticmethod
    def wait_for_processing(timeout=2.0):
        """Wait for background processing to complete"""
        time.sleep(timeout)
    
    @staticmethod
    def measure_execution_time(func, *args, **kwargs):
        """Measure execution time of a function"""
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        execution_time = end_time - start_time
        return result, execution_time
    
    @staticmethod
    def measure_memory_usage(func, *args, **kwargs):
        """Measure memory usage of a function"""
        process = psutil.Process()
        memory_before = process.memory_info().rss
        
        result = func(*args, **kwargs)
        
        memory_after = process.memory_info().rss
        memory_increase = memory_after - memory_before
        
        return result, memory_increase
    
    @staticmethod
    def cleanup_test_data():
        """Clean up test data after tests"""
        from discovery.models import (
            DataAsset, ClassificationResult, RealTimeMonitor, 
            MonitoringEvent, DataDiscoveryInsight
        )
        
        # Clean up in reverse dependency order
        MonitoringEvent.objects.filter(
            event_data__contains='test'
        ).delete()
        
        DataDiscoveryInsight.objects.filter(
            metadata__contains='test'
        ).delete()
        
        ClassificationResult.objects.filter(
            metadata__contains='test'
        ).delete()
        
        DataAsset.objects.filter(
            name__contains='Test'
        ).delete()
        
        RealTimeMonitor.objects.filter(
            name__contains='Test'
        ).delete()


class TestDataGenerator:
    """Generate test data for various scenarios"""
    
    @staticmethod
    def generate_pii_content():
        """Generate content with PII data"""
        return [
            "My email is john.doe@example.com and SSN is 123-45-6789",
            "Contact info: jane.smith@company.com, phone: (555) 123-4567",
            "Driver's license: DL123456789, DOB: 01/15/1985",
            "Home address: 123 Main St, Anytown, ST 12345"
        ]
    
    @staticmethod
    def generate_phi_content():
        """Generate content with PHI data"""
        return [
            "Patient John Doe, MRN: 123456, diagnosed with diabetes",
            "Blood pressure: 120/80, weight: 180lbs, allergies: penicillin",
            "Prescription: Metformin 500mg twice daily",
            "Insurance: BlueCross ID BC123456789"
        ]
    
    @staticmethod
    def generate_financial_content():
        """Generate content with financial data"""
        return [
            "Credit card: 4532-1234-5678-9012, exp: 12/25, CVV: 123",
            "Bank account: 123456789, routing: 021000021",
            "Investment account: INV123456, balance: $50,000",
            "Tax ID: 12-3456789, annual income: $75,000"
        ]
    
    @staticmethod
    def generate_credentials_content():
        """Generate content with credentials"""
        return [
            "Username: admin, Password: P@ssw0rd123",
            "API key: sk-1234567890abcdef",
            "Database: user:password@localhost:5432/db",
            "SSH key: ssh-rsa AAAAB3NzaC1yc2EAAAADAQAB..."
        ]
    
    @staticmethod
    def generate_public_content():
        """Generate public content that should not be classified as sensitive"""
        return [
            "Welcome to our company website!",
            "We provide excellent customer service",
            "Contact us at info@company.com for more information",
            "Follow us on social media for updates"
        ]
    
    @staticmethod
    def generate_mixed_content():
        """Generate content with mixed classification types"""
        return [
            "Customer: John Doe, Email: john@example.com, CC: 4532-1234-5678-9012, SSN: 123-45-6789",
            "Patient record: Jane Smith, MRN: P123456, Insurance: BC987654321, DOB: 02/20/1990",
            "Employee data: Bob Johnson, ID: E12345, Salary: $65,000, SSN: 987-65-4321"
        ]


class PerformanceBenchmarks:
    """Performance benchmarking utilities"""
    
    @staticmethod
    def benchmark_classification_engine(sample_size=100):
        """Benchmark classification engine performance"""
        from discovery.classification_engine import DataClassificationEngine, ContentContext
        
        engine = DataClassificationEngine()
        test_content = TestDataGenerator.generate_pii_content() * (sample_size // 4)
        
        context = ContentContext(
            content_type="messaging.message",
            model_name="message",
            app_name="messaging"
        )
        
        start_time = time.time()
        
        for content in test_content:
            engine.classify_content(content, context)
            
        end_time = time.time()
        
        total_time = end_time - start_time
        avg_time_per_item = total_time / len(test_content)
        
        return {
            'total_time': total_time,
            'items_processed': len(test_content),
            'avg_time_per_item': avg_time_per_item,
            'items_per_second': len(test_content) / total_time
        }
    
    @staticmethod
    def benchmark_governance_orchestrator(sample_size=50):
        """Benchmark governance orchestrator performance"""
        from discovery.governance import GovernanceOrchestrator
        
        # Create test data
        user = TestUtilities.create_test_user('benchuser')
        orchestrator = GovernanceOrchestrator()
        
        # Create test assets and classifications
        test_assets = []
        for i in range(sample_size):
            asset = TestUtilities.create_test_data_asset(user, 'PII')
            test_assets.append(asset)
        
        start_time = time.time()
        
        # Apply governance to all assets
        for asset in test_assets:
            classifications = asset.classificationresult_set.all()
            for classification in classifications:
                orchestrator.process_classification_result(classification)
                
        end_time = time.time()
        
        total_time = end_time - start_time
        avg_time_per_asset = total_time / sample_size
        
        return {
            'total_time': total_time,
            'assets_processed': sample_size,
            'avg_time_per_asset': avg_time_per_asset,
            'assets_per_second': sample_size / total_time
        }
    
    @staticmethod
    def benchmark_api_endpoints(sample_size=10):
        """Benchmark API endpoint performance"""
        from django.test import Client
        from django.contrib.auth.models import User
        
        client = Client()
        user = User.objects.create_user(
            username='apitest',
            email='api@example.com',
            password='testpass123'
        )
        client.force_login(user)
        
        endpoints = [
            '/api/discovery/dashboard/',
            '/api/discovery/governance-dashboard/',
        ]
        
        results = {}
        
        for endpoint in endpoints:
            response_times = []
            
            for _ in range(sample_size):
                start_time = time.time()
                response = client.get(endpoint)
                end_time = time.time()
                
                if response.status_code == 200:
                    response_times.append(end_time - start_time)
            
            if response_times:
                results[endpoint] = {
                    'avg_response_time': sum(response_times) / len(response_times),
                    'min_response_time': min(response_times),
                    'max_response_time': max(response_times),
                    'successful_requests': len(response_times)
                }
        
        return results


def run_discovery_tests():
    """Run all discovery system tests with comprehensive reporting"""
    import unittest
    
    # Set up test environment
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'destroyer.settings')
    
    # Import test modules
    from . import test_classification_accuracy
    from . import test_api_endpoints  
    from . import test_integration_realtime
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromModule(test_classification_accuracy))
    suite.addTests(loader.loadTestsFromModule(test_api_endpoints))
    suite.addTests(loader.loadTestsFromModule(test_integration_realtime))
    
    # Run tests with custom runner
    runner = TextTestRunner(verbosity=2, stream=sys.stdout)
    
    print("="*60)
    print("RUNNING DISCOVERY SYSTEM COMPREHENSIVE TEST SUITE")
    print("="*60)
    
    # Record start time
    start_time = time.time()
    
    # Run tests
    result = runner.run(suite)
    
    # Record end time
    end_time = time.time()
    total_time = end_time - start_time
    
    # Print summary
    print("\n" + "="*60)
    print("TEST EXECUTION SUMMARY")
    print("="*60)
    print(f"Total tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.2f}%")
    print(f"Total execution time: {total_time:.2f} seconds")
    print(f"Average time per test: {total_time / result.testsRun:.3f} seconds")
    
    # Run performance benchmarks
    print("\n" + "="*60)
    print("PERFORMANCE BENCHMARKS")
    print("="*60)
    
    try:
        classification_benchmark = PerformanceBenchmarks.benchmark_classification_engine()
        print(f"Classification Engine:")
        print(f"  - Items per second: {classification_benchmark['items_per_second']:.2f}")
        print(f"  - Avg time per item: {classification_benchmark['avg_time_per_item']:.4f}s")
        
        governance_benchmark = PerformanceBenchmarks.benchmark_governance_orchestrator()
        print(f"Governance Orchestrator:")
        print(f"  - Assets per second: {governance_benchmark['assets_per_second']:.2f}")
        print(f"  - Avg time per asset: {governance_benchmark['avg_time_per_asset']:.4f}s")
        
        api_benchmark = PerformanceBenchmarks.benchmark_api_endpoints()
        print(f"API Endpoints:")
        for endpoint, metrics in api_benchmark.items():
            print(f"  {endpoint}: {metrics['avg_response_time']:.3f}s avg")
            
    except Exception as e:
        print(f"Benchmark error: {e}")
    
    print("="*60)
    
    return result


if __name__ == '__main__':
    run_discovery_tests()
