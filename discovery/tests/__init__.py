"""
Discovery System Test Suite

This package contains comprehensive tests for the data discovery system including:
- Classification accuracy tests across different data types
- API endpoint testing for dashboards and governance
- Real-time monitoring and integration tests
- Performance benchmarking and load testing
- End-to-end workflow validation

Test Modules:
- test_classification_accuracy: Tests for classification engine accuracy and rules
- test_api_endpoints: API testing for discovery and governance dashboards  
- test_integration_realtime: Integration and real-time monitoring tests
- test_runner: Test runner utilities and performance benchmarks

Usage:
    python manage.py test discovery.tests
    
    Or run with custom test runner:
    python discovery/tests/test_runner.py
"""

# Import main test utilities for easy access
from .test_runner import (
    DiscoveryTestRunner,
    TestUtilities,
    TestDataGenerator,
    PerformanceBenchmarks,
    run_discovery_tests
)

__version__ = '1.0.0'
__author__ = 'Data Discovery Team'

# Test configuration
TEST_SETTINGS = {
    'classification_accuracy_threshold': 0.75,
    'api_response_time_threshold': 2.0,
    'concurrent_request_timeout': 10.0,
    'memory_usage_threshold_mb': 100.0,
    'false_positive_rate_threshold': 0.1,
    'performance_benchmark_sample_size': 100
}

# Export test utilities
__all__ = [
    'DiscoveryTestRunner',
    'TestUtilities', 
    'TestDataGenerator',
    'PerformanceBenchmarks',
    'run_discovery_tests',
    'TEST_SETTINGS'
]
