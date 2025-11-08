"""
Active Learning Training Pipeline for ML Classification

This module handles converting user feedback into training data
and fine-tuning spaCy NER models with the corrected annotations.
"""

import json
import logging
import random
from pathlib import Path
from typing import Dict, List, Tuple

import spacy
from django.conf import settings
from spacy.training import Example
from spacy.util import minibatch

from .ml_models import (
    ClassificationFeedback,
    MLModel,
    ModelMetric,
    TrainingBatch,
    TrainingDataset,
)

logger = logging.getLogger(__name__)


class TrainingDataConverter:
    """
    Convert user feedback and training datasets into spaCy training format.
    """

    @staticmethod
    def feedback_to_training_data(
        feedback_queryset=None, limit: int = None
    ) -> List[Tuple[str, Dict]]:
        """
        Convert ClassificationFeedback records to spaCy training format.

        Args:
            feedback_queryset: QuerySet of ClassificationFeedback objects
            limit: Maximum number of samples to convert

        Returns:
            List of (text, annotations) tuples in spaCy format
        """
        if feedback_queryset is None:
            # Get unincorporated incorrect feedback
            feedback_queryset = ClassificationFeedback.objects.filter(
                is_correct=False, incorporated_in_training=False
            ).select_related("result")

        if limit:
            feedback_queryset = feedback_queryset[:limit]

        training_data = []

        for feedback in feedback_queryset:
            if not feedback.corrected_entities:
                continue

            text = feedback.result.text
            entities = []

            # Convert entities to spaCy format: (start, end, label)
            for entity in feedback.corrected_entities:
                start = entity.get("start")
                end = entity.get("end")
                label = entity.get("sublabel") or entity.get("label")

                if start is not None and end is not None and label:
                    entities.append((start, end, label))

            if entities:
                annotations = {"entities": entities}
                training_data.append((text, annotations))

        logger.info(f"Converted {len(training_data)} feedback items to training data")
        return training_data

    @staticmethod
    def training_dataset_to_spacy_format(
        dataset_queryset=None, limit: int = None
    ) -> List[Tuple[str, Dict]]:
        """
        Convert TrainingDataset records to spaCy training format.

        Args:
            dataset_queryset: QuerySet of TrainingDataset objects
            limit: Maximum number of samples to convert

        Returns:
            List of (text, annotations) tuples in spaCy format
        """
        if dataset_queryset is None:
            # Get verified training data
            dataset_queryset = TrainingDataset.objects.filter(verified=True)

        if limit:
            dataset_queryset = dataset_queryset[:limit]

        training_data = []

        for dataset in dataset_queryset:
            text = dataset.text
            entities = []

            for entity in dataset.entities:
                start = entity.get("start")
                end = entity.get("end")
                label = entity.get("sublabel") or entity.get("label")

                if start is not None and end is not None and label:
                    entities.append((start, end, label))

            if entities:
                annotations = {"entities": entities}
                training_data.append((text, annotations))

                # Increment usage count
                dataset.usage_count += 1
                dataset.save(update_fields=["usage_count"])

        logger.info(f"Converted {len(training_data)} dataset items to training data")
        return training_data


class ModelTrainer:
    """
    Fine-tune spaCy NER models with user feedback and training data.
    """

    def __init__(self, model_name: str = "en_core_web_sm", use_gpu: bool = False):
        """
        Initialize the model trainer.

        Args:
            model_name: Base spaCy model to fine-tune
            use_gpu: Whether to use GPU for training
        """
        self.model_name = model_name
        self.use_gpu = use_gpu
        self.nlp = None

    def prepare_training_data(
        self, include_feedback: bool = True, include_datasets: bool = True
    ) -> List[Tuple[str, Dict]]:
        """
        Prepare training data from feedback and/or training datasets.

        Args:
            include_feedback: Include user feedback corrections
            include_datasets: Include verified training datasets

        Returns:
            Combined training data in spaCy format
        """
        training_data = []

        if include_feedback:
            feedback_data = TrainingDataConverter.feedback_to_training_data()
            training_data.extend(feedback_data)

        if include_datasets:
            dataset_data = TrainingDataConverter.training_dataset_to_spacy_format()
            training_data.extend(dataset_data)

        # Shuffle for better training
        random.shuffle(training_data)

        logger.info(f"Prepared {len(training_data)} training samples")
        return training_data

    def load_model(self):
        """Load the base spaCy model"""
        try:
            self.nlp = spacy.load(self.model_name)
            logger.info(f"Loaded model: {self.model_name}")
        except OSError:
            logger.warning(
                f"Model {self.model_name} not found, creating blank English model"
            )
            self.nlp = spacy.blank("en")
            # Add NER pipe if not present
            if "ner" not in self.nlp.pipe_names:
                ner = self.nlp.add_pipe("ner")
                logger.info("Added NER pipe to blank model")

    def add_labels(self, training_data: List[Tuple[str, Dict]]):
        """
        Add all entity labels from training data to the NER pipe.

        Args:
            training_data: Training data in spaCy format
        """
        if "ner" not in self.nlp.pipe_names:
            raise ValueError("NER pipe not found in model")

        ner = self.nlp.get_pipe("ner")
        labels_added = set()

        for text, annotations in training_data:
            for start, end, label in annotations.get("entities", []):
                if label not in labels_added:
                    ner.add_label(label)
                    labels_added.add(label)

        logger.info(f"Added {len(labels_added)} labels to model: {labels_added}")

    def train(
        self,
        training_data: List[Tuple[str, Dict]],
        n_iter: int = 30,
        batch_size: int = 8,
        drop: float = 0.5,
    ) -> Dict:
        """
        Fine-tune the model on training data.

        Args:
            training_data: Training data in spaCy format
            n_iter: Number of training iterations
            batch_size: Batch size for training
            drop: Dropout rate

        Returns:
            Dictionary with training metrics
        """
        if self.nlp is None:
            self.load_model()

        # Add labels from training data
        self.add_labels(training_data)

        # Convert to Example format
        examples = []
        for text, annotations in training_data:
            doc = self.nlp.make_doc(text)
            example = Example.from_dict(doc, annotations)
            examples.append(example)

        # Get the NER component
        ner = self.nlp.get_pipe("ner")

        # Disable other pipes during training
        other_pipes = [pipe for pipe in self.nlp.pipe_names if pipe != "ner"]
        with self.nlp.disable_pipes(*other_pipes):
            # Initialize optimizer if model was loaded
            if self.model_name != "blank":
                optimizer = self.nlp.resume_training()
            else:
                optimizer = self.nlp.initialize()

            # Training loop
            losses_history = []

            for iteration in range(n_iter):
                random.shuffle(examples)
                losses = {}

                # Batch training
                batches = minibatch(examples, size=batch_size)

                for batch in batches:
                    self.nlp.update(
                        batch,
                        drop=drop,
                        losses=losses,
                        sgd=optimizer,
                    )

                losses_history.append(losses.get("ner", 0))

                if iteration % 5 == 0:
                    logger.info(
                        f"Iteration {iteration}/{n_iter}, Loss: {losses.get('ner', 0):.4f}"
                    )

        metrics = {
            "iterations": n_iter,
            "final_loss": losses_history[-1] if losses_history else 0,
            "average_loss": sum(losses_history) / len(losses_history)
            if losses_history
            else 0,
            "training_samples": len(training_data),
        }

        logger.info(f"Training completed: {metrics}")
        return metrics

    def evaluate(self, test_data: List[Tuple[str, Dict]]) -> Dict:
        """
        Evaluate model performance on test data.

        Args:
            test_data: Test data in spaCy format

        Returns:
            Dictionary with evaluation metrics
        """
        if self.nlp is None:
            raise ValueError("Model not loaded")

        # Convert to examples
        examples = []
        for text, annotations in test_data:
            doc = self.nlp.make_doc(text)
            example = Example.from_dict(doc, annotations)
            examples.append(example)

        # Evaluate
        scores = self.nlp.evaluate(examples)

        metrics = {
            "precision": scores.get("ents_p", 0),
            "recall": scores.get("ents_r", 0),
            "f1_score": scores.get("ents_f", 0),
            "test_samples": len(test_data),
        }

        logger.info(f"Evaluation results: {metrics}")
        return metrics

    def save_model(self, output_dir: str) -> str:
        """
        Save the trained model to disk.

        Args:
            output_dir: Directory to save the model

        Returns:
            Path to saved model
        """
        if self.nlp is None:
            raise ValueError("No model to save")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        self.nlp.to_disk(output_path)
        logger.info(f"Model saved to: {output_path}")

        return str(output_path)


class ActiveLearningPipeline:
    """
    Complete active learning pipeline from feedback to trained model.
    """

    def __init__(self, model_name: str = "en_core_web_sm"):
        self.model_name = model_name
        self.trainer = ModelTrainer(model_name=model_name)

    def run_training_cycle(
        self,
        n_iter: int = 30,
        test_split: float = 0.2,
        min_samples: int = 10,
    ) -> Dict:
        """
        Run a complete training cycle:
        1. Collect feedback and training data
        2. Split into train/test
        3. Train model
        4. Evaluate performance
        5. Save model and metrics

        Args:
            n_iter: Number of training iterations
            test_split: Fraction of data to use for testing
            min_samples: Minimum samples required to train

        Returns:
            Dictionary with training results
        """
        # Create training batch record
        batch = TrainingBatch.objects.create(
            model_type="spacy_ner",
            status="running",
            configuration={
                "model_name": self.model_name,
                "n_iter": n_iter,
                "test_split": test_split,
            },
        )

        try:
            # Prepare training data
            training_data = self.trainer.prepare_training_data(
                include_feedback=True, include_datasets=True
            )

            if len(training_data) < min_samples:
                batch.status = "failed"
                batch.error_message = (
                    f"Insufficient training data: {len(training_data)} < {min_samples}"
                )
                batch.save()
                return {"status": "failed", "reason": batch.error_message}

            # Split data
            split_idx = int(len(training_data) * (1 - test_split))
            train_data = training_data[:split_idx]
            test_data = training_data[split_idx:]

            batch.sample_count = len(train_data)
            batch.save()

            # Train model
            logger.info(
                f"Training on {len(train_data)} samples, testing on {len(test_data)}"
            )
            train_metrics = self.trainer.train(train_data, n_iter=n_iter)

            # Evaluate model
            eval_metrics = self.trainer.evaluate(test_data)

            # Save model
            model_dir = Path(settings.BASE_DIR) / "models" / f"model_{batch.id}"
            model_path = self.trainer.save_model(str(model_dir))

            # Create MLModel record
            ml_model = MLModel.objects.create(
                name=f"Active Learning Model - {batch.id}",
                model_type="spacy_ner",
                version=f"v{MLModel.objects.count() + 1}",
                file_path=model_path,
                accuracy=eval_metrics.get("f1_score", 0),
                precision=eval_metrics.get("precision", 0),
                recall=eval_metrics.get("recall", 0),
                f1_score=eval_metrics.get("f1_score", 0),
                training_samples=len(train_data),
                is_active=False,  # Requires manual activation
            )

            # Record metrics
            for metric_type, value in eval_metrics.items():
                ModelMetric.objects.create(
                    model=ml_model, metric_type=metric_type, metric_value=value
                )

            # Update batch status
            batch.status = "completed"
            batch.metrics = {**train_metrics, **eval_metrics}
            batch.completed_at = timezone.now()
            batch.save()

            # Mark feedback as incorporated
            ClassificationFeedback.objects.filter(
                is_correct=False, incorporated_in_training=False
            ).update(incorporated_in_training=True)

            logger.info(f"Training cycle completed successfully: {ml_model.id}")

            return {
                "status": "completed",
                "model_id": str(ml_model.id),
                "batch_id": str(batch.id),
                "metrics": {**train_metrics, **eval_metrics},
                "model_path": model_path,
            }

        except Exception as e:
            logger.error(f"Training failed: {e}", exc_info=True)
            batch.status = "failed"
            batch.error_message = str(e)
            batch.save()
            return {"status": "failed", "error": str(e)}


# Import timezone for batch completion timestamp
from django.utils import timezone
