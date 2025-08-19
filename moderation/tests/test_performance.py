"""
Performance tests for the moderation system

Tests scanning performance, bulk operations, and system scalability.
"""

import statistics
import time

from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase

from moderation.content_analyzer import ContentAnalyzer
from moderation.models import ContentScan, PolicyViolation, SensitiveContentPattern

User = get_user_model()


class ModerationPerformanceTestCase(TestCase):
    """Test performance characteristics of the moderation system"""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")

        # Create test patterns
        self.patterns = []
        pattern_configs = [
            ("SSN Pattern", "pii_detected", r"\d{3}-?\d{2}-?\d{4}"),
            ("Credit Card", "financial_data", r"\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}"),
            (
                "Email Pattern",
                "pii_detected",
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            ),
            ("Phone Pattern", "pii_detected", r"\(?([0-9]{3})\)?[-. ]?([0-9]{3})[-. ]?([0-9]{4})"),
        ]

        for name, violation_type, pattern in pattern_configs:
            self.patterns.append(
                SensitiveContentPattern.objects.create(
                    name=name, pattern_type=violation_type, regex_pattern=pattern, is_active=True
                )
            )

    def test_single_content_scan_performance(self):
        """Test performance of scanning a single piece of content"""
        test_content = """
        Hello, my name is John Smith and my email is john.smith@example.com.
        My phone number is (555) 123-4567 and my SSN is 123-45-6789.
        My credit card number is 4532-1234-5678-9012.
        """

        analyzer = ContentAnalyzer()

        # Warm up
        analyzer.analyze_content("test content")

        # Time multiple runs
        execution_times = []
        for _ in range(10):
            start_time = time.time()
            result = analyzer.analyze_content(test_content)
            execution_time = (time.time() - start_time) * 1000  # Convert to ms
            execution_times.append(execution_time)

        avg_time = statistics.mean(execution_times)
        max_time = max(execution_times)
        min_time = min(execution_times)

        print("\nSingle Content Scan Performance:")
        print(f"Average time: {avg_time:.2f}ms")
        print(f"Min time: {min_time:.2f}ms")
        print(f"Max time: {max_time:.2f}ms")
        print(f"Violations found: {result.violations_found}")

        # Assert performance requirements
        self.assertLess(avg_time, 100, "Average scan time should be under 100ms")
        self.assertLess(max_time, 500, "Max scan time should be under 500ms")
        self.assertEqual(result.violations_found, 4, "Should detect 4 violations")

    def test_bulk_content_scan_performance(self):
        """Test performance of bulk scanning operations"""
        # Generate test content
        test_contents = []
        for i in range(100):
            content = f"""
            Document {i}: Email test{i}@example.com, phone (555) {i:03d}-{i:04d}.
            SSN: {123 + i:03d}-{45 + i:02d}-{6789 + i:04d}.
            Credit Card: 4532-{1234 + i:04d}-5678-9012.
            """
            test_contents.append(content)

        analyzer = ContentAnalyzer()

        # Test bulk scanning
        start_time = time.time()
        results = []
        for content in test_contents:
            result = analyzer.analyze_content(content)
            results.append(result)

        total_time = (time.time() - start_time) * 1000
        avg_time_per_item = total_time / len(test_contents)
        total_violations = sum(r.violations_found for r in results)

        print("\nBulk Content Scan Performance (100 items):")
        print(f"Total time: {total_time:.2f}ms")
        print(f"Average time per item: {avg_time_per_item:.2f}ms")
        print(f"Total violations found: {total_violations}")
        print(f"Items per second: {len(test_contents) / (total_time / 1000):.1f}")

        # Assert performance requirements
        self.assertLess(avg_time_per_item, 50, "Bulk scan should average under 50ms per item")
        self.assertGreater(total_violations, 300, "Should find violations in bulk content")

    def test_pattern_matching_complexity(self):
        """Test performance with different pattern complexities"""
        # Simple pattern
        simple_pattern = SensitiveContentPattern.objects.create(
            name="Simple Pattern",
            pattern_type="custom_pattern",
            regex_pattern=r"test",
            is_active=True,
        )

        # Complex pattern
        complex_pattern = SensitiveContentPattern.objects.create(
            name="Complex Pattern",
            pattern_type="custom_pattern",
            regex_pattern=r"(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}",
            is_active=True,
        )

        test_content = "This is a test content with password Password123! and simple test."

        analyzer = ContentAnalyzer()

        # Test with simple pattern only
        simple_pattern.is_active = True
        complex_pattern.is_active = False
        analyzer.refresh_patterns()

        simple_times = []
        for _ in range(10):
            start_time = time.time()
            analyzer.analyze_content(test_content)
            simple_times.append((time.time() - start_time) * 1000)

        # Test with complex pattern only
        simple_pattern.is_active = False
        complex_pattern.is_active = True
        analyzer.refresh_patterns()

        complex_times = []
        for _ in range(10):
            start_time = time.time()
            analyzer.analyze_content(test_content)
            complex_times.append((time.time() - start_time) * 1000)

        avg_simple = statistics.mean(simple_times)
        avg_complex = statistics.mean(complex_times)

        print("\nPattern Complexity Performance:")
        print(f"Simple pattern average: {avg_simple:.2f}ms")
        print(f"Complex pattern average: {avg_complex:.2f}ms")
        print(f"Complexity overhead: {avg_complex - avg_simple:.2f}ms")

        # Complex patterns may be slower but should still be reasonable
        self.assertLess(avg_complex, 20, "Complex patterns should still be under 20ms")

    def test_memory_usage_bulk_operations(self):
        """Test memory efficiency during bulk operations"""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Create large amount of test content
        large_content_batch = []
        for i in range(500):
            content = (
                f"""
            Large content block {i} with multiple violations:
            Email: user{i}@example{i}.com
            Phone: (555) {i:03d}-{i+1000:04d}
            SSN: {100+i:03d}-{50+i:02d}-{7000+i:04d}
            Credit: 4532-{2000+i:04d}-5678-9012
            Additional text to make content larger and test memory usage
            with scanning operations across many patterns and content blocks.
            """
                * 3
            )  # Triple the content size
            large_content_batch.append(content)

        analyzer = ContentAnalyzer()

        # Process all content
        for content in large_content_batch:
            result = analyzer.analyze_content(content)

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        print("\nMemory Usage Test:")
        print(f"Initial memory: {initial_memory:.2f} MB")
        print(f"Final memory: {final_memory:.2f} MB")
        print(f"Memory increase: {memory_increase:.2f} MB")
        print(f"Memory per item: {memory_increase / len(large_content_batch):.3f} MB")

        # Assert reasonable memory usage (should not grow excessively)
        self.assertLess(memory_increase, 100, "Memory increase should be under 100MB for 500 items")


class DatabasePerformanceTestCase(TransactionTestCase):
    """Test database performance for moderation operations"""

    def setUp(self):
        self.user = User.objects.create_user(username="perftest", password="testpass123")

        # Create patterns
        for i in range(10):
            SensitiveContentPattern.objects.create(
                name=f"Pattern {i}",
                pattern_type="pii_detected",
                regex_pattern=f"test{i}",
                is_active=True,
            )

    def test_content_scan_database_performance(self):
        """Test database operations during content scanning"""
        from django.db import connection

        # Reset query count
        connection.queries_log.clear()

        test_content = "This contains test0, test1, test2 patterns"

        analyzer = ContentAnalyzer()

        with self.assertNumQueriesLessThan(20):  # Should be efficient
            result = analyzer.analyze_content(test_content)

        print("\nDatabase Performance:")
        print(f"Queries executed: {len(connection.queries)}")
        print(f"Violations found: {result.violations_found}")

        # Test query efficiency
        self.assertLess(len(connection.queries), 15, "Should execute efficiently")

    def test_bulk_violation_creation_performance(self):
        """Test performance of creating many violations"""
        from django.db import transaction

        # Create a content scan
        content_scan = ContentScan.objects.create(
            user=self.user,
            content_type_id=1,
            object_id="test",
            content_length=1000,
            processing_time_ms=50,
            scan_status="completed",
        )

        patterns = list(SensitiveContentPattern.objects.all())

        # Time bulk violation creation
        start_time = time.time()

        with transaction.atomic():
            violations = []
            for i, pattern in enumerate(patterns):
                violations.append(
                    PolicyViolation(
                        content_scan=content_scan,
                        pattern=pattern,
                        violation_type=pattern.pattern_type,
                        severity="medium",
                        matched_content=f"test{i}",
                        match_count=1,
                    )
                )

            PolicyViolation.objects.bulk_create(violations)

        bulk_time = (time.time() - start_time) * 1000

        print("\nBulk Violation Creation:")
        print(f"Created {len(violations)} violations in {bulk_time:.2f}ms")
        print(f"Time per violation: {bulk_time / len(violations):.2f}ms")

        self.assertLess(bulk_time, 100, "Bulk creation should be under 100ms")
        self.assertEqual(PolicyViolation.objects.count(), len(patterns))


class ScalabilityTestCase(TestCase):
    """Test system scalability with increasing loads"""

    def setUp(self):
        self.users = []
        for i in range(5):
            user = User.objects.create_user(username=f"scaleuser{i}", password="testpass123")
            self.users.append(user)

        # Create patterns
        SensitiveContentPattern.objects.create(
            name="Scale Test Pattern",
            pattern_type="pii_detected",
            regex_pattern=r"scale\d+",
            is_active=True,
        )

    def test_concurrent_user_scanning(self):
        """Test performance with multiple users scanning simultaneously"""
        test_contents = [
            f"User {i} content with scale{i*10} pattern" for i in range(len(self.users))
        ]

        analyzer = ContentAnalyzer()

        # Simulate concurrent scanning
        start_time = time.time()
        results = []

        for i, user in enumerate(self.users):
            result = analyzer.analyze_content(test_contents[i])
            results.append(result)

        total_time = (time.time() - start_time) * 1000
        avg_time = total_time / len(self.users)

        print("\nConcurrent User Scanning:")
        print(f"Total time for {len(self.users)} users: {total_time:.2f}ms")
        print(f"Average time per user: {avg_time:.2f}ms")
        print(f"Total violations: {sum(r.violations_found for r in results)}")

        self.assertLess(avg_time, 100, "Concurrent scanning should maintain performance")

    def test_pattern_scaling(self):
        """Test performance as number of patterns increases"""
        base_patterns = 5
        test_patterns = [10, 25, 50]

        results = {}
        analyzer = ContentAnalyzer()
        test_content = "This content has scale0, scale1, scale2 patterns"

        for pattern_count in test_patterns:
            # Create additional patterns
            current_count = SensitiveContentPattern.objects.count()
            for i in range(current_count, pattern_count):
                SensitiveContentPattern.objects.create(
                    name=f"Scale Pattern {i}",
                    pattern_type="pii_detected",
                    regex_pattern=f"scale{i}",
                    is_active=True,
                )

            analyzer.refresh_patterns()

            # Time scanning with this many patterns
            scan_times = []
            for _ in range(5):
                start_time = time.time()
                analyzer.analyze_content(test_content)
                scan_times.append((time.time() - start_time) * 1000)

            avg_time = statistics.mean(scan_times)
            results[pattern_count] = avg_time

        print("\nPattern Scaling Test:")
        for count, time_ms in results.items():
            print(f"{count} patterns: {time_ms:.2f}ms average")

        # Performance should scale reasonably
        max_time = max(results.values())
        min_time = min(results.values())

        self.assertLess(max_time / min_time, 5, "Performance degradation should be reasonable")
        self.assertLess(max_time, 200, "Even with many patterns, should stay under 200ms")


def run_performance_benchmarks():
    """
    Utility function to run all performance benchmarks
    Can be called from management commands or tests
    """
    import unittest

    # Create test suite
    suite = unittest.TestSuite()

    # Add performance test cases
    suite.addTest(unittest.makeSuite(ModerationPerformanceTestCase))
    suite.addTest(unittest.makeSuite(DatabasePerformanceTestCase))
    suite.addTest(unittest.makeSuite(ScalabilityTestCase))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return {
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "success": result.wasSuccessful(),
    }
