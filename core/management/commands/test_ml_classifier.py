"""
Test the ML classification engine with sample texts.

Usage:
    python manage.py test_ml_classifier
    python manage.py test_ml_classifier --text "Your custom text here"
    python manage.py test_ml_classifier --no-ml  # Regex only
    python manage.py test_ml_classifier --no-regex  # ML only
"""

from django.core.management.base import BaseCommand

from discovery.ml import HybridClassificationEngine


class Command(BaseCommand):
    help = "Test ML classification engine with sample texts"

    def add_arguments(self, parser):
        parser.add_argument(
            "--text",
            type=str,
            help="Custom text to classify",
        )
        parser.add_argument(
            "--no-ml",
            action="store_true",
            help="Disable ML classification (regex only)",
        )
        parser.add_argument(
            "--no-regex",
            action="store_true",
            help="Disable regex classification (ML only)",
        )
        parser.add_argument(
            "--types",
            type=str,
            help="Comma-separated classification types (e.g., PII,PHI)",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("🤖 Testing ML Classification Engine\n"))

        # Parse options
        use_ml = not options["no_ml"]
        use_regex = not options["no_regex"]
        classification_types = None

        if options["types"]:
            classification_types = [t.strip() for t in options["types"].split(",")]

        # Initialize engine
        self.stdout.write(f"Initializing engine (ML: {use_ml}, Regex: {use_regex})...")
        engine = HybridClassificationEngine(use_ml=use_ml, use_regex=use_regex)

        # Sample texts
        sample_texts = [
            "John Smith's SSN is 123-45-6789 and email is john@example.com",
            "Call me at (555) 123-4567 or email jane.doe@company.com",
            "Credit card: 4532-1234-5678-9010, expires 12/25",
            "Patient MRN-123456 has diabetes and takes Metformin 500mg",
            "IP address 192.168.1.1 accessed by admin@internal.net",
        ]

        # Use custom text if provided
        if options["text"]:
            sample_texts = [options["text"]]

        # Classify each text
        for i, text in enumerate(sample_texts, 1):
            self.stdout.write(f"\n{'='*80}")
            self.stdout.write(self.style.WARNING(f"\nSample {i}:"))
            self.stdout.write(f"Text: {text}\n")

            # Classify
            result = engine.classify(text, classification_types)

            # Display results
            if result.has_entities:
                self.stdout.write(self.style.SUCCESS(f"Found {result.entity_count} entities:\n"))

                for entity in result.entities:
                    self.stdout.write(
                        f"  • {entity.text:30s} "
                        f"[{entity.label}/{entity.sublabel:15s}] "
                        f"confidence: {entity.confidence:.2f} "
                        f"({entity.source.value})"
                    )

                self.stdout.write(
                    f"\nOverall confidence: {result.overall_confidence:.2f}"
                )
                self.stdout.write(
                    f"Processing time: {result.processing_time_ms:.0f}ms"
                )
                self.stdout.write(
                    f"Regex entities: {len(result.regex_entities)}, "
                    f"ML entities: {len(result.ml_entities)}, "
                    f"Merged: {len(result.entities)}"
                )
            else:
                self.stdout.write(self.style.ERROR("No entities found"))

        # Engine statistics
        self.stdout.write(f"\n{'='*80}")
        self.stdout.write(self.style.SUCCESS("\nEngine Statistics:"))
        stats = engine.get_statistics()
        for key, value in stats.items():
            if isinstance(value, dict):
                self.stdout.write(f"  {key}:")
                for k, v in value.items():
                    self.stdout.write(f"    {k}: {v}")
            else:
                self.stdout.write(f"  {key}: {value}")

        self.stdout.write(self.style.SUCCESS("\n\n✅ Testing complete!"))
