"""
Accuracy tests for the moderation system

Tests detection accuracy, false positive/negative rates, and pattern effectiveness.
"""

import unittest

from django.contrib.auth import get_user_model
from django.test import TestCase

from moderation.content_analyzer import ContentAnalyzer
from moderation.models import SensitiveContentPattern

User = get_user_model()


class PIIDetectionAccuracyTestCase(TestCase):
    """Test accuracy of PII detection patterns"""

    def setUp(self):
        self.user = User.objects.create_user(username="accuracytest", password="testpass123")

        # Create comprehensive PII patterns
        self.create_pii_patterns()
        self.analyzer = ContentAnalyzer()

    def create_pii_patterns(self):
        """Create comprehensive PII detection patterns"""
        patterns = [
            # SSN patterns
            ("SSN Standard", "pii_detected", r"\b\d{3}-\d{2}-\d{4}\b"),
            ("SSN No Dashes", "pii_detected", r"\b\d{9}\b"),
            ("SSN Spaces", "pii_detected", r"\b\d{3}\s\d{2}\s\d{4}\b"),
            # Phone number patterns
            (
                "Phone Standard",
                "pii_detected",
                r"\b\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b",
            ),
            (
                "Phone International",
                "pii_detected",
                r"\b\+?1?[-.\s]?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b",
            ),
            # Email patterns
            (
                "Email Standard",
                "pii_detected",
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            ),
            # Credit card patterns
            ("Credit Card Visa", "financial_data", r"\b4[0-9]{12}(?:[0-9]{3})?\b"),
            (
                "Credit Card Generic",
                "financial_data",
                r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
            ),
            # Driver's License (example format)
            ("Drivers License", "pii_detected", r"\b[A-Z]\d{7}\b"),
            # Bank account patterns
            ("Bank Account", "financial_data", r"\b\d{8,12}\b"),
            # Medical ID patterns
            ("Medical ID", "medical_data", r"\b[A-Z]{2}\d{8}\b"),
        ]

        for name, pattern_type, regex in patterns:
            SensitiveContentPattern.objects.create(
                name=name, pattern_type=pattern_type, regex_pattern=regex, is_active=True
            )

    def test_ssn_detection_accuracy(self):
        """Test SSN detection with various formats"""
        test_cases = [
            # True positives (should detect)
            ("123-45-6789", True, "Standard SSN format"),
            ("987-65-4321", True, "Another standard SSN"),
            ("123456789", True, "SSN without dashes"),
            ("123 45 6789", True, "SSN with spaces"),
            ("My SSN is 555-44-3333 for reference", True, "SSN in sentence"),
            # True negatives (should NOT detect)
            ("123-456-7890", False, "Phone number format"),
            ("12-34-56", False, "Too short"),
            ("1234-56-7890", False, "Wrong format"),
            ("abc-de-fghi", False, "Non-numeric"),
            ("000-00-0000", False, "Invalid SSN"),  # This might be debatable
        ]

        results = self._test_pattern_accuracy(test_cases, "SSN")
        self._assert_accuracy_metrics(results, min_precision=0.9, min_recall=0.8)

    def test_phone_detection_accuracy(self):
        """Test phone number detection accuracy"""
        test_cases = [
            # True positives
            ("(555) 123-4567", True, "Standard phone format"),
            ("555-123-4567", True, "Dash format"),
            ("555.123.4567", True, "Dot format"),
            ("555 123 4567", True, "Space format"),
            ("+1 555 123 4567", True, "International format"),
            ("Call me at (800) 555-1234", True, "Phone in sentence"),
            # True negatives
            ("123-45-6789", False, "SSN format"),
            ("555-12-345", False, "Wrong grouping"),
            ("55-123-4567", False, "Too few digits in area code"),
            ("abc-def-ghij", False, "Non-numeric"),
            ("1234567890123", False, "Too many digits"),
        ]

        results = self._test_pattern_accuracy(test_cases, "Phone")
        self._assert_accuracy_metrics(results, min_precision=0.85, min_recall=0.8)

    def test_email_detection_accuracy(self):
        """Test email detection accuracy"""
        test_cases = [
            # True positives
            ("user@example.com", True, "Basic email"),
            ("test.user@example.com", True, "Email with dot"),
            ("user+tag@example.co.uk", True, "Email with plus and multiple TLD"),
            ("firstname.lastname@company.org", True, "Corporate email"),
            ("Contact me at john.smith@example.com please", True, "Email in sentence"),
            ("user123@test-domain.com", True, "Email with numbers and dash"),
            # True negatives
            ("user@", False, "Incomplete email"),
            ("@example.com", False, "Missing user part"),
            ("user@example", False, "Missing TLD"),
            ("user.example.com", False, "Missing @ symbol"),
            ("user@ex ample.com", False, "Space in domain"),
            ("user@@example.com", False, "Double @ symbol"),
        ]

        results = self._test_pattern_accuracy(test_cases, "Email")
        self._assert_accuracy_metrics(results, min_precision=0.95, min_recall=0.9)

    def test_credit_card_detection_accuracy(self):
        """Test credit card detection accuracy"""
        test_cases = [
            # True positives
            ("4532123456789012", True, "Visa card"),
            ("4532-1234-5678-9012", True, "Visa with dashes"),
            ("4532 1234 5678 9012", True, "Visa with spaces"),
            ("My card is 4111-1111-1111-1111", True, "Card in sentence"),
            # True negatives
            ("123-45-6789", False, "SSN format"),
            ("555-123-4567", False, "Phone format"),
            ("45321234567890123", False, "Too many digits"),
            ("453212345678901", False, "Too few digits"),
            ("abcd-efgh-ijkl-mnop", False, "Non-numeric"),
        ]

        results = self._test_pattern_accuracy(test_cases, "Credit Card")
        self._assert_accuracy_metrics(results, min_precision=0.9, min_recall=0.85)

    def test_false_positive_resistance(self):
        """Test resistance to false positives with common text"""
        false_positive_texts = [
            "The year 1985 was significant",
            "Room 123 on floor 4567",
            "Product code ABC-DEF-GHI",
            "Time 12:34:56 PM",
            "Date 12/34/5678 format",
            "ISBN 978-0123456789",
            "Version 1.2.3.4567",
            "IP address 192.168.1.1",
            "Hex color #123456",
            "Mathematical expression 123 + 456 = 579",
            "File size 1234567890 bytes",
            "Temperature 98.6 degrees",
            "Price $123.45",
            "Percentage 12.34%",
            "Coordinates 40.7128, -74.0060",
        ]

        false_positives = 0
        total_texts = len(false_positive_texts)

        for text in false_positive_texts:
            result = self.analyzer.analyze_content(text)
            if result.violations_found > 0:
                false_positives += 1
                print(f"False positive in: '{text}' - found {result.violations_found} violations")

        false_positive_rate = false_positives / total_texts
        print("\\nFalse Positive Test:")
        print(f"False positives: {false_positives}/{total_texts}")
        print(f"False positive rate: {false_positive_rate:.2%}")

        # Assert acceptable false positive rate
        self.assertLess(false_positive_rate, 0.2, "False positive rate should be under 20%")

    def test_context_sensitivity(self):
        """Test detection in various contexts"""
        context_tests = [
            # Should detect in all contexts
            ("My SSN is 123-45-6789", True, "Direct statement"),
            ("Please provide SSN: 123-45-6789", True, "Form context"),
            ("SSN 123-45-6789 for verification", True, "Verification context"),
            ("Confidential: SSN 123-45-6789", True, "Confidential context"),
            # Email contexts
            ("Send to user@example.com", True, "Email instruction"),
            ("From: user@example.com", True, "Email header"),
            ("Reply to user@example.com with questions", True, "Email reference"),
            # Phone contexts
            ("Call (555) 123-4567 for support", True, "Support context"),
            ("Emergency contact: (555) 123-4567", True, "Emergency context"),
            ("Fax: (555) 123-4567", True, "Fax context"),
        ]

        correct_detections = 0
        total_tests = len(context_tests)

        for text, should_detect, context in context_tests:
            result = self.analyzer.analyze_content(text)
            detected = result.violations_found > 0

            if detected == should_detect:
                correct_detections += 1
            else:
                print(f"Context test failed: '{text}' - Expected: {should_detect}, Got: {detected}")

        accuracy = correct_detections / total_tests
        print("\\nContext Sensitivity Test:")
        print(f"Correct detections: {correct_detections}/{total_tests}")
        print(f"Context accuracy: {accuracy:.2%}")

        self.assertGreater(accuracy, 0.9, "Context accuracy should be over 90%")

    def test_mixed_content_accuracy(self):
        """Test accuracy with mixed PII types in single content"""
        mixed_content_tests = [
            {
                "content": "John Smith, SSN: 123-45-6789, Email: john@example.com, Phone: (555) 123-4567",
                "expected_violations": 3,
                "description": "Multiple PII types",
            },
            {
                "content": "Employee ID: E123456, Email: employee@company.com, Card: 4532-1234-5678-9012",
                "expected_violations": 2,  # Email and card (Employee ID might not match patterns)
                "description": "Employee information",
            },
            {
                "content": "Patient: Jane Doe, DOB: 01/01/1990, Phone: 555.123.4567, Medical ID: AB12345678",
                "expected_violations": 2,  # Phone and Medical ID
                "description": "Medical information",
            },
        ]

        for test_case in mixed_content_tests:
            result = self.analyzer.analyze_content(test_case["content"])
            violations_found = result.violations_found
            expected = test_case["expected_violations"]

            print(f"\\nMixed content test: {test_case['description']}")
            print(f"Expected violations: {expected}, Found: {violations_found}")
            print(f"Content: {test_case['content']}")

            # Allow some tolerance in mixed content detection
            tolerance = 1
            self.assertAlmostEqual(
                violations_found,
                expected,
                delta=tolerance,
                msg=f"Violations detection off by more than {tolerance} for: {test_case['description']}",
            )

    def _test_pattern_accuracy(self, test_cases, pattern_name):
        """Helper method to test pattern accuracy"""
        true_positives = 0
        true_negatives = 0
        false_positives = 0
        false_negatives = 0

        for text, should_detect, description in test_cases:
            result = self.analyzer.analyze_content(text)
            detected = result.violations_found > 0

            if should_detect and detected:
                true_positives += 1
            elif not should_detect and not detected:
                true_negatives += 1
            elif not should_detect and detected:
                false_positives += 1
                print(f"False positive for {pattern_name}: '{text}' - {description}")
            else:  # should_detect and not detected
                false_negatives += 1
                print(f"False negative for {pattern_name}: '{text}' - {description}")

        total_positive = true_positives + false_negatives
        total_negative = true_negatives + false_positives

        precision = (
            true_positives / (true_positives + false_positives)
            if (true_positives + false_positives) > 0
            else 0
        )
        recall = (
            true_positives / (true_positives + false_negatives)
            if (true_positives + false_negatives) > 0
            else 0
        )
        accuracy = (true_positives + true_negatives) / len(test_cases)
        f1_score = (
            2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        )

        results = {
            "pattern_name": pattern_name,
            "true_positives": true_positives,
            "true_negatives": true_negatives,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            "precision": precision,
            "recall": recall,
            "accuracy": accuracy,
            "f1_score": f1_score,
            "total_tests": len(test_cases),
        }

        print(f"\\n{pattern_name} Detection Accuracy:")
        print(f"Precision: {precision:.2%}")
        print(f"Recall: {recall:.2%}")
        print(f"Accuracy: {accuracy:.2%}")
        print(f"F1 Score: {f1_score:.3f}")
        print(f"Total tests: {len(test_cases)}")

        return results

    def _assert_accuracy_metrics(self, results, min_precision=0.8, min_recall=0.7):
        """Assert minimum accuracy metrics"""
        self.assertGreater(
            results["precision"],
            min_precision,
            f"{results['pattern_name']} precision {results['precision']:.2%} below minimum {min_precision:.2%}",
        )
        self.assertGreater(
            results["recall"],
            min_recall,
            f"{results['pattern_name']} recall {results['recall']:.2%} below minimum {min_recall:.2%}",
        )


class PatternEffectivenessTestCase(TestCase):
    """Test effectiveness of different pattern configurations"""

    def setUp(self):
        self.user = User.objects.create_user(username="patterntest", password="testpass123")
        self.analyzer = ContentAnalyzer()

    def test_case_sensitivity_patterns(self):
        """Test case sensitive vs case insensitive patterns"""
        # Create case sensitive pattern
        case_sensitive = SensitiveContentPattern.objects.create(
            name="Case Sensitive Test",
            pattern_type="custom_pattern",
            regex_pattern=r"SECRET",
            case_sensitive=True,
            is_active=True,
        )

        test_cases = [
            ("This contains SECRET information", True),
            ("This contains secret information", False),  # Should not match
            ("This contains Secret information", False),  # Should not match
        ]

        for content, should_match in test_cases:
            matches = case_sensitive.test_content(content)
            matched = len(matches) > 0
            self.assertEqual(
                matched, should_match, f"Case sensitivity test failed for: '{content}'"
            )

        print("\\nCase Sensitivity Test: PASSED")

    def test_word_boundary_patterns(self):
        """Test whole word vs partial matching"""
        # Pattern with word boundaries
        word_boundary = SensitiveContentPattern.objects.create(
            name="Word Boundary Test",
            pattern_type="custom_pattern",
            regex_pattern=r"\\btest\\b",
            match_whole_words=True,
            is_active=True,
        )

        test_cases = [
            ("This is a test case", True),  # Should match
            ("Testing the function", False),  # Should not match (partial)
            ("Protest the decision", False),  # Should not match (partial)
            ("test", True),  # Should match (exact)
        ]

        for content, should_match in test_cases:
            matches = word_boundary.test_content(content)
            matched = len(matches) > 0
            self.assertEqual(matched, should_match, f"Word boundary test failed for: '{content}'")

        print("Word Boundary Test: PASSED")

    def test_minimum_matches_threshold(self):
        """Test minimum matches threshold functionality"""
        # Pattern requiring multiple matches
        multi_match = SensitiveContentPattern.objects.create(
            name="Multi Match Test",
            pattern_type="custom_pattern",
            regex_pattern=r"data",
            minimum_matches=3,
            is_active=True,
        )

        test_cases = [
            ("data", 1, False),  # 1 match, below threshold
            ("data and more data", 2, False),  # 2 matches, below threshold
            ("data, data, and more data", 3, True),  # 3 matches, meets threshold
            ("data data data data", 4, True),  # 4 matches, above threshold
        ]

        for content, expected_count, should_trigger in test_cases:
            matches = multi_match.test_content(content)
            match_count = len(matches)
            triggered = len(matches) >= multi_match.minimum_matches

            self.assertEqual(
                match_count,
                expected_count,
                f"Match count wrong for: '{content}' - expected {expected_count}, got {match_count}",
            )
            self.assertEqual(triggered, should_trigger, f"Threshold trigger wrong for: '{content}'")

        print("Minimum Matches Test: PASSED")


class EdgeCaseTestCase(TestCase):
    """Test edge cases and unusual scenarios"""

    def setUp(self):
        self.user = User.objects.create_user(username="edgetest", password="testpass123")

        # Create standard patterns
        SensitiveContentPattern.objects.create(
            name="SSN Edge Test",
            pattern_type="pii_detected",
            regex_pattern=r"\\b\\d{3}-\\d{2}-\\d{4}\\b",
            is_active=True,
        )

        self.analyzer = ContentAnalyzer()

    def test_empty_and_whitespace_content(self):
        """Test handling of empty and whitespace-only content"""
        edge_cases = [
            ("", 0, "Empty string"),
            ("   ", 0, "Whitespace only"),
            ("\\n\\n\\n", 0, "Newlines only"),
            ("\\t\\t", 0, "Tabs only"),
            ("   123-45-6789   ", 1, "SSN with surrounding whitespace"),
        ]

        for content, expected_violations, description in edge_cases:
            result = self.analyzer.analyze_content(content)
            self.assertEqual(
                result.violations_found, expected_violations, f"Edge case failed: {description}"
            )

        print("Empty/Whitespace Content Test: PASSED")

    def test_very_large_content(self):
        """Test performance with very large content blocks"""
        # Generate large content with embedded PII
        large_content = "This is filler text. " * 1000  # ~20KB of text
        large_content += "Hidden SSN: 123-45-6789 in large content."
        large_content += "More filler text. " * 1000

        result = self.analyzer.analyze_content(large_content)

        # Should still detect the SSN
        self.assertEqual(result.violations_found, 1, "Should detect SSN in large content")
        # Should complete in reasonable time
        self.assertLess(result.processing_time_ms, 1000, "Should process large content quickly")

        print(
            f"Large Content Test: PASSED - {len(large_content)} chars processed in {result.processing_time_ms}ms"
        )

    def test_unicode_and_special_characters(self):
        """Test handling of unicode and special characters"""
        unicode_tests = [
            ("Café user: josé@example.com", 1, "Unicode in email"),
            ("Phone: ☎ (555) 123-4567", 1, "Unicode symbol with phone"),
            ("SSN: 123-45-6789 ✓", 1, "SSN with checkmark"),
            ("邮箱：user@example.com", 1, "Chinese text with email"),
            ("Tél: (555) 123-4567", 1, "French text with phone"),
        ]

        # Add email pattern for these tests
        SensitiveContentPattern.objects.create(
            name="Email Unicode Test",
            pattern_type="pii_detected",
            regex_pattern=r"\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b",
            is_active=True,
        )

        # Add phone pattern
        SensitiveContentPattern.objects.create(
            name="Phone Unicode Test",
            pattern_type="pii_detected",
            regex_pattern=r"\\(?([0-9]{3})\\)?[-. ]?([0-9]{3})[-. ]?([0-9]{4})",
            is_active=True,
        )

        for content, expected_violations, description in unicode_tests:
            result = self.analyzer.analyze_content(content)
            self.assertEqual(
                result.violations_found, expected_violations, f"Unicode test failed: {description}"
            )

        print("Unicode/Special Characters Test: PASSED")

    def test_malformed_patterns(self):
        """Test handling of potentially malformed input"""
        malformed_tests = [
            ("123-45-", 0, "Incomplete SSN"),
            ("123-45-67890", 0, "Extra digit SSN"),
            ("@example.com", 0, "Email without user"),
            ("user@", 0, "Email without domain"),
            ("555-123-456", 0, "Incomplete phone"),
            ("(555 123-4567", 0, "Unmatched parenthesis phone"),
        ]

        for content, expected_violations, description in malformed_tests:
            result = self.analyzer.analyze_content(content)
            self.assertEqual(
                result.violations_found,
                expected_violations,
                f"Malformed pattern test failed: {description}",
            )

        print("Malformed Patterns Test: PASSED")


def run_accuracy_tests():
    """
    Utility function to run all accuracy tests
    Can be called from management commands
    """

    # Create test suite
    suite = unittest.TestSuite()

    # Add accuracy test cases
    suite.addTest(unittest.makeSuite(PIIDetectionAccuracyTestCase))
    suite.addTest(unittest.makeSuite(PatternEffectivenessTestCase))
    suite.addTest(unittest.makeSuite(EdgeCaseTestCase))

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
    # Allow running accuracy tests directly
    run_accuracy_tests()
