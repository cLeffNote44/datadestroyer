"""
Django management command to run comprehensive moderation system tests

Usage:
  python manage.py run_moderation_tests
  python manage.py run_moderation_tests --test-type performance
  python manage.py run_moderation_tests --test-type accuracy
  python manage.py run_moderation_tests --test-type integration
"""

import time

from django.core.management.base import BaseCommand

from moderation.tests.test_accuracy import run_accuracy_tests
from moderation.tests.test_integration import run_integration_tests
from moderation.tests.test_performance import run_performance_benchmarks


class Command(BaseCommand):
    help = "Run comprehensive moderation system tests including performance, accuracy, and integration tests"

    def add_arguments(self, parser):
        parser.add_argument(
            "--test-type",
            type=str,
            choices=["all", "performance", "accuracy", "integration"],
            default="all",
            help="Type of tests to run (default: all)",
        )

        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Enable verbose output",
        )

        parser.add_argument(
            "--benchmark",
            action="store_true",
            help="Run additional benchmarking tests",
        )

    def handle(self, *args, **options):
        test_type = options["test_type"]
        verbose = options["verbose"]
        benchmark = options["benchmark"]

        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("🔍 MODERATION SYSTEM COMPREHENSIVE TEST SUITE"))
        self.stdout.write(self.style.SUCCESS("=" * 60))

        start_time = time.time()

        # Test results summary
        results = {"performance": None, "accuracy": None, "integration": None}

        # Run Performance Tests
        if test_type in ["all", "performance"]:
            self.stdout.write("\n" + "🚀 RUNNING PERFORMANCE TESTS")
            self.stdout.write("-" * 40)

            try:
                perf_start = time.time()
                results["performance"] = run_performance_benchmarks()
                perf_time = time.time() - perf_start

                if results["performance"]["success"]:
                    self.stdout.write(
                        self.style.SUCCESS(f"✅ Performance tests completed in {perf_time:.2f}s")
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f"❌ Performance tests failed with {results['performance']['failures']} failures"
                        )
                    )

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"💥 Performance tests crashed: {str(e)}"))
                results["performance"] = {"success": False, "error": str(e)}

        # Run Accuracy Tests
        if test_type in ["all", "accuracy"]:
            self.stdout.write("\n" + "🎯 RUNNING ACCURACY TESTS")
            self.stdout.write("-" * 40)

            try:
                acc_start = time.time()
                results["accuracy"] = run_accuracy_tests()
                acc_time = time.time() - acc_start

                if results["accuracy"]["success"]:
                    self.stdout.write(
                        self.style.SUCCESS(f"✅ Accuracy tests completed in {acc_time:.2f}s")
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f"❌ Accuracy tests failed with {results['accuracy']['failures']} failures"
                        )
                    )

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"💥 Accuracy tests crashed: {str(e)}"))
                results["accuracy"] = {"success": False, "error": str(e)}

        # Run Integration Tests
        if test_type in ["all", "integration"]:
            self.stdout.write("\n" + "🔧 RUNNING INTEGRATION TESTS")
            self.stdout.write("-" * 40)

            try:
                int_start = time.time()
                results["integration"] = run_integration_tests()
                int_time = time.time() - int_start

                if results["integration"]["success"]:
                    self.stdout.write(
                        self.style.SUCCESS(f"✅ Integration tests completed in {int_time:.2f}s")
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f"❌ Integration tests failed with {results['integration']['failures']} failures"
                        )
                    )

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"💥 Integration tests crashed: {str(e)}"))
                results["integration"] = {"success": False, "error": str(e)}

        # Run Additional Benchmarks
        if benchmark:
            self.stdout.write("\n" + "📊 RUNNING ADDITIONAL BENCHMARKS")
            self.stdout.write("-" * 40)
            self._run_system_benchmarks()

        # Print Final Summary
        total_time = time.time() - start_time
        self._print_final_summary(results, total_time, test_type)

        # Exit with appropriate code
        if self._all_tests_passed(results):
            self.stdout.write(
                self.style.SUCCESS("\n🎉 ALL TESTS PASSED! System ready for production.")
            )
        else:
            self.stdout.write(
                self.style.ERROR("\n⚠️  SOME TESTS FAILED! Review results before deployment.")
            )
            exit(1)

    def _run_system_benchmarks(self):
        """Run additional system benchmarks"""
        from moderation.content_analyzer import ContentAnalyzer
        from moderation.models import ContentScan, SensitiveContentPattern

        self.stdout.write("Running system benchmarks...")

        # Pattern count benchmark
        pattern_count = SensitiveContentPattern.objects.filter(is_active=True).count()
        self.stdout.write(f"📋 Active patterns: {pattern_count}")

        # Content scan statistics
        scan_count = ContentScan.objects.count()
        avg_processing_time = (
            ContentScan.objects.aggregate(avg_time=models.Avg("processing_time_ms"))["avg_time"]
            or 0
        )

        self.stdout.write(f"📊 Total scans performed: {scan_count}")
        self.stdout.write(f"⚡ Average processing time: {avg_processing_time:.2f}ms")

        # Memory usage benchmark
        try:
            import os

            import psutil

            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            self.stdout.write(f"💾 Current memory usage: {memory_mb:.2f} MB")
        except ImportError:
            self.stdout.write("💾 Memory monitoring not available (install psutil)")

        # Quick performance test
        analyzer = ContentAnalyzer()
        test_content = "Quick benchmark: SSN 123-45-6789, email test@example.com"

        benchmark_times = []
        for _ in range(10):
            start = time.time()
            analyzer.analyze_content(test_content)
            benchmark_times.append((time.time() - start) * 1000)

        avg_benchmark_time = sum(benchmark_times) / len(benchmark_times)
        self.stdout.write(f"⚡ Real-time scan performance: {avg_benchmark_time:.2f}ms average")

    def _print_final_summary(self, results, total_time, test_type):
        """Print comprehensive test summary"""

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("📈 TEST SUMMARY REPORT"))
        self.stdout.write("=" * 60)

        # Overall stats
        total_tests = 0
        total_failures = 0
        total_errors = 0

        for test_name, result in results.items():
            if result:
                total_tests += result.get("tests_run", 0)
                total_failures += result.get("failures", 0)
                total_errors += result.get("errors", 0)

        self.stdout.write(f"📊 Test execution time: {total_time:.2f} seconds")
        self.stdout.write(f"🧪 Total tests executed: {total_tests}")
        self.stdout.write(f"❌ Total failures: {total_failures}")
        self.stdout.write(f"💥 Total errors: {total_errors}")

        # Individual test results
        for test_name, result in results.items():
            if result is None:
                continue

            if result.get("success", False):
                status_icon = "✅"
                status_text = self.style.SUCCESS("PASSED")
            else:
                status_icon = "❌"
                status_text = self.style.ERROR("FAILED")

            tests_run = result.get("tests_run", 0)
            failures = result.get("failures", 0)
            errors = result.get("errors", 0)

            self.stdout.write(f"\n{status_icon} {test_name.upper()} TESTS: {status_text}")
            self.stdout.write(f"   Tests: {tests_run}, Failures: {failures}, Errors: {errors}")

            if "error" in result:
                self.stdout.write(f"   Error: {result['error']}")

        # Recommendations based on results
        self._print_recommendations(results)

    def _print_recommendations(self, results):
        """Print recommendations based on test results"""

        self.stdout.write("\n" + "💡 RECOMMENDATIONS:")
        self.stdout.write("-" * 30)

        recommendations = []

        # Performance recommendations
        if results.get("performance") and not results["performance"].get("success", True):
            recommendations.append(
                "⚡ Performance: Review slow operations and optimize pattern complexity"
            )

        # Accuracy recommendations
        if results.get("accuracy") and not results["accuracy"].get("success", True):
            recommendations.append(
                "🎯 Accuracy: Review detection patterns for false positives/negatives"
            )

        # Integration recommendations
        if results.get("integration") and not results["integration"].get("success", True):
            recommendations.append(
                "🔧 Integration: Check API endpoints and workflow configurations"
            )

        # General recommendations
        recommendations.extend(
            [
                "📚 Documentation: Ensure all features are documented",
                "🚀 Deployment: Run tests in staging environment before production",
                "📊 Monitoring: Set up performance monitoring in production",
                "🔒 Security: Review privacy settings and access controls",
            ]
        )

        for rec in recommendations:
            self.stdout.write(f"  • {rec}")

    def _all_tests_passed(self, results):
        """Check if all executed tests passed"""
        for result in results.values():
            if result is not None and not result.get("success", False):
                return False
        return True


# Utility functions for external use
def run_full_test_suite():
    """
    Run the complete test suite programmatically
    Returns comprehensive results dictionary
    """
    results = {}

    try:
        results["performance"] = run_performance_benchmarks()
    except Exception as e:
        results["performance"] = {"success": False, "error": str(e)}

    try:
        results["accuracy"] = run_accuracy_tests()
    except Exception as e:
        results["accuracy"] = {"success": False, "error": str(e)}

    try:
        results["integration"] = run_integration_tests()
    except Exception as e:
        results["integration"] = {"success": False, "error": str(e)}

    return results


def validate_production_readiness():
    """
    Validate if the moderation system is ready for production
    Returns (is_ready: bool, issues: List[str])
    """
    results = run_full_test_suite()
    issues = []

    for test_type, result in results.items():
        if not result.get("success", False):
            issues.append(f"{test_type.title()} tests failed")

    # Additional production readiness checks
    from moderation.models import SensitiveContentPattern

    active_patterns = SensitiveContentPattern.objects.filter(is_active=True).count()
    if active_patterns == 0:
        issues.append("No active detection patterns configured")

    # Check for required settings
    from django.conf import settings

    if not hasattr(settings, "DEFAULT_FROM_EMAIL"):
        issues.append("Email configuration missing")

    is_ready = len(issues) == 0
    return is_ready, issues
