"""
Django management command to load built-in content moderation patterns.

Usage:
    python manage.py load_moderation_patterns
    python manage.py load_moderation_patterns --update-existing
    python manage.py load_moderation_patterns --category pii
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from moderation.content_analyzer import BuiltInPatterns
from moderation.models import SensitiveContentPattern, SensitivityLevel, ViolationType


class Command(BaseCommand):
    help = "Load built-in content moderation patterns into the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--update-existing",
            action="store_true",
            help="Update existing patterns with new definitions",
        )
        parser.add_argument(
            "--category",
            choices=["pii", "financial", "medical", "legal"],
            help="Load only patterns from a specific category",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without actually creating it",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        update_existing = options["update_existing"]
        category_filter = options["category"]

        self.stdout.write(
            self.style.SUCCESS(
                f"{'[DRY RUN] ' if dry_run else ''}Loading built-in moderation patterns..."
            )
        )

        patterns_data = self._get_patterns_data(category_filter)

        created_count = 0
        updated_count = 0
        skipped_count = 0

        with transaction.atomic():
            for pattern_info in patterns_data:
                existing = SensitiveContentPattern.objects.filter(name=pattern_info["name"]).first()

                if existing:
                    if update_existing:
                        if not dry_run:
                            for key, value in pattern_info.items():
                                setattr(existing, key, value)
                            existing.save()
                        updated_count += 1
                        self.stdout.write(f"  Updated: {pattern_info['name']}")
                    else:
                        skipped_count += 1
                        self.stdout.write(f"  Skipped (exists): {pattern_info['name']}")
                else:
                    if not dry_run:
                        SensitiveContentPattern.objects.create(**pattern_info)
                    created_count += 1
                    self.stdout.write(f"  Created: {pattern_info['name']}")

            if dry_run:
                # Don't commit in dry run mode
                transaction.set_rollback(True)

        # Summary
        self.stdout.write(
            self.style.SUCCESS(f"\n{'[DRY RUN] ' if dry_run else ''}Pattern loading completed:")
        )
        self.stdout.write(f"  Created: {created_count}")
        self.stdout.write(f"  Updated: {updated_count}")
        self.stdout.write(f"  Skipped: {skipped_count}")

    def _get_patterns_data(self, category_filter=None):
        """Get pattern data to load, optionally filtered by category"""

        all_patterns = BuiltInPatterns.get_all_patterns()
        patterns_to_load = []

        # Pattern definitions with metadata
        pattern_definitions = {
            # PII Patterns
            "ssn_standard": {
                "name": "Social Security Number (Standard)",
                "description": "Detects SSN in XXX-XX-XXXX format",
                "sensitivity_level": SensitivityLevel.CRITICAL,
                "auto_quarantine": True,
            },
            "ssn_no_dashes": {
                "name": "Social Security Number (No Dashes)",
                "description": "Detects 9-digit SSN without formatting",
                "sensitivity_level": SensitivityLevel.HIGH,
                "auto_quarantine": False,
            },
            "ssn_spaces": {
                "name": "Social Security Number (Spaces)",
                "description": "Detects SSN with spaces: XXX XX XXXX",
                "sensitivity_level": SensitivityLevel.CRITICAL,
                "auto_quarantine": True,
            },
            "us_phone": {
                "name": "US Phone Number",
                "description": "Detects US phone numbers in various formats",
                "sensitivity_level": SensitivityLevel.MEDIUM,
                "auto_quarantine": False,
            },
            "international": {
                "name": "International Phone Number",
                "description": "Detects international phone numbers with country codes",
                "sensitivity_level": SensitivityLevel.MEDIUM,
                "auto_quarantine": False,
            },
            "email": {
                "name": "Email Address",
                "description": "Detects email addresses",
                "sensitivity_level": SensitivityLevel.LOW,
                "auto_quarantine": False,
            },
            "ca_license": {
                "name": "California Driver's License",
                "description": "California DL format: A1234567",
                "sensitivity_level": SensitivityLevel.HIGH,
                "auto_quarantine": False,
            },
            "ny_license": {
                "name": "New York Driver's License",
                "description": "New York DL format: 123-123-123",
                "sensitivity_level": SensitivityLevel.HIGH,
                "auto_quarantine": False,
            },
            "fl_license": {
                "name": "Florida Driver's License",
                "description": "Florida DL format: A123-123-12-123-1",
                "sensitivity_level": SensitivityLevel.HIGH,
                "auto_quarantine": False,
            },
            "passport": {
                "name": "Passport Number",
                "description": "US passport numbers",
                "sensitivity_level": SensitivityLevel.CRITICAL,
                "auto_quarantine": True,
            },
            "ein": {
                "name": "Employer ID Number (EIN)",
                "description": "Federal tax ID numbers: XX-XXXXXXX",
                "sensitivity_level": SensitivityLevel.HIGH,
                "auto_quarantine": False,
            },
            "itin": {
                "name": "Individual Taxpayer ID (ITIN)",
                "description": "ITINs starting with 9: 9XX-XX-XXXX",
                "sensitivity_level": SensitivityLevel.CRITICAL,
                "auto_quarantine": True,
            },
            # Financial Patterns
            "visa": {
                "name": "Visa Credit Card",
                "description": "Visa credit card numbers starting with 4",
                "sensitivity_level": SensitivityLevel.CRITICAL,
                "auto_quarantine": True,
            },
            "mastercard": {
                "name": "Mastercard Credit Card",
                "description": "Mastercard numbers starting with 51-55",
                "sensitivity_level": SensitivityLevel.CRITICAL,
                "auto_quarantine": True,
            },
            "amex": {
                "name": "American Express Card",
                "description": "AmEx card numbers starting with 34/37",
                "sensitivity_level": SensitivityLevel.CRITICAL,
                "auto_quarantine": True,
            },
            "discover": {
                "name": "Discover Credit Card",
                "description": "Discover card numbers starting with 6011/65XX",
                "sensitivity_level": SensitivityLevel.CRITICAL,
                "auto_quarantine": True,
            },
            "routing_number": {
                "name": "Bank Routing Number",
                "description": "9-digit US bank routing numbers",
                "sensitivity_level": SensitivityLevel.HIGH,
                "auto_quarantine": False,
            },
            "account_number": {
                "name": "Bank Account Number",
                "description": "Bank account numbers (8-17 digits)",
                "sensitivity_level": SensitivityLevel.CRITICAL,
                "auto_quarantine": True,
            },
            "iban": {
                "name": "International Bank Account (IBAN)",
                "description": "International bank account numbers",
                "sensitivity_level": SensitivityLevel.CRITICAL,
                "auto_quarantine": True,
            },
            # Medical Patterns
            "insurance_id": {
                "name": "Health Insurance ID",
                "description": "Health insurance member IDs",
                "sensitivity_level": SensitivityLevel.HIGH,
                "auto_quarantine": False,
            },
            "medicare_number": {
                "name": "Medicare Number",
                "description": "Medicare beneficiary numbers",
                "sensitivity_level": SensitivityLevel.CRITICAL,
                "auto_quarantine": True,
            },
            "npi_number": {
                "name": "National Provider Identifier (NPI)",
                "description": "Healthcare provider NPI numbers",
                "sensitivity_level": SensitivityLevel.MEDIUM,
                "auto_quarantine": False,
            },
            "medical_record": {
                "name": "Medical Record Number (MRN)",
                "description": "Hospital medical record numbers",
                "sensitivity_level": SensitivityLevel.HIGH,
                "auto_quarantine": False,
            },
            # Legal Patterns
            "case_number": {
                "name": "Legal Case Number",
                "description": "Court case reference numbers",
                "sensitivity_level": SensitivityLevel.MEDIUM,
                "auto_quarantine": False,
            },
            "docket_number": {
                "name": "Court Docket Number",
                "description": "Court docket numbers starting with 'No.'",
                "sensitivity_level": SensitivityLevel.MEDIUM,
                "auto_quarantine": False,
            },
            "court_case": {
                "name": "Court Case Name",
                "description": "Case names in 'v. Name' format",
                "sensitivity_level": SensitivityLevel.LOW,
                "auto_quarantine": False,
            },
        }

        # Map violation types
        violation_type_map = {
            "pii": ViolationType.PII_DETECTED,
            "financial": ViolationType.FINANCIAL_DATA,
            "medical": ViolationType.MEDICAL_DATA,
            "legal": ViolationType.LEGAL_DATA,
        }

        # Build patterns list
        for category, patterns in all_patterns.items():
            if category_filter and category != category_filter:
                continue

            for pattern_key, regex_pattern in patterns.items():
                if pattern_key not in pattern_definitions:
                    # Skip undefined patterns
                    continue

                definition = pattern_definitions[pattern_key]

                pattern_data = {
                    "name": definition["name"],
                    "pattern_type": violation_type_map[category],
                    "regex_pattern": regex_pattern,
                    "description": definition["description"],
                    "sensitivity_level": definition["sensitivity_level"],
                    "is_active": True,
                    "auto_quarantine": definition["auto_quarantine"],
                    "case_sensitive": False,
                    "match_whole_words": True,
                    "minimum_matches": 1,
                }

                patterns_to_load.append(pattern_data)

        return patterns_to_load
