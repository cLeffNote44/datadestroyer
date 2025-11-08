"""
Management command to train ML models from user feedback.

Usage:
    python manage.py train_ml_model
    python manage.py train_ml_model --iterations 50
    python manage.py train_ml_model --model en_core_web_trf
    python manage.py train_ml_model --min-samples 20
"""

from django.core.management.base import BaseCommand

from discovery.ml.training import ActiveLearningPipeline


class Command(BaseCommand):
    help = "Train ML classification models using collected user feedback"

    def add_arguments(self, parser):
        parser.add_argument(
            "--model",
            type=str,
            default="en_core_web_sm",
            help="Base spaCy model to fine-tune (default: en_core_web_sm)",
        )

        parser.add_argument(
            "--iterations",
            type=int,
            default=30,
            help="Number of training iterations (default: 30)",
        )

        parser.add_argument(
            "--test-split",
            type=float,
            default=0.2,
            help="Fraction of data for testing (default: 0.2)",
        )

        parser.add_argument(
            "--min-samples",
            type=int,
            default=10,
            help="Minimum training samples required (default: 10)",
        )

    def handle(self, *args, **options):
        model_name = options["model"]
        n_iter = options["iterations"]
        test_split = options["test_split"]
        min_samples = options["min_samples"]

        self.stdout.write(
            self.style.SUCCESS(
                f"\n{'='*60}\nML Model Training Pipeline\n{'='*60}\n"
            )
        )

        self.stdout.write(f"Base model: {model_name}")
        self.stdout.write(f"Iterations: {n_iter}")
        self.stdout.write(f"Test split: {test_split}")
        self.stdout.write(f"Min samples: {min_samples}\n")

        # Initialize pipeline
        pipeline = ActiveLearningPipeline(model_name=model_name)

        # Run training cycle
        self.stdout.write(self.style.WARNING("Starting training cycle...\n"))

        result = pipeline.run_training_cycle(
            n_iter=n_iter, test_split=test_split, min_samples=min_samples
        )

        # Display results
        if result["status"] == "completed":
            self.stdout.write(self.style.SUCCESS("\n✓ Training completed successfully!\n"))

            self.stdout.write(f"Model ID: {result['model_id']}")
            self.stdout.write(f"Batch ID: {result['batch_id']}")
            self.stdout.write(f"Model saved to: {result['model_path']}\n")

            # Display metrics
            metrics = result["metrics"]
            self.stdout.write(self.style.SUCCESS("Training Metrics:"))
            self.stdout.write(f"  Training samples: {metrics.get('training_samples', 0)}")
            self.stdout.write(f"  Iterations: {metrics.get('iterations', 0)}")
            self.stdout.write(f"  Final loss: {metrics.get('final_loss', 0):.4f}")
            self.stdout.write(
                f"  Average loss: {metrics.get('average_loss', 0):.4f}\n"
            )

            self.stdout.write(self.style.SUCCESS("Evaluation Metrics:"))
            self.stdout.write(f"  Precision: {metrics.get('precision', 0):.4f}")
            self.stdout.write(f"  Recall: {metrics.get('recall', 0):.4f}")
            self.stdout.write(f"  F1 Score: {metrics.get('f1_score', 0):.4f}")
            self.stdout.write(f"  Test samples: {metrics.get('test_samples', 0)}\n")

            self.stdout.write(
                self.style.WARNING(
                    "\nNote: New model is NOT active by default."
                    "\nReview the metrics and activate it manually if performance is good."
                )
            )

        elif result["status"] == "failed":
            self.stdout.write(self.style.ERROR(f"\n✗ Training failed!"))
            if "error" in result:
                self.stdout.write(self.style.ERROR(f"Error: {result['error']}"))
            if "reason" in result:
                self.stdout.write(self.style.ERROR(f"Reason: {result['reason']}"))

        self.stdout.write(self.style.SUCCESS(f"\n{'='*60}\n"))
