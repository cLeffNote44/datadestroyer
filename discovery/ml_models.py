"""
Machine Learning models for advanced data classification.

These models enable ML-powered classification with active learning,
model versioning, and performance tracking.
"""

import uuid

from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class ModelType(models.TextChoices):
    """Types of ML models"""

    SPACY_NER = "spacy_ner", "spaCy NER"
    TRANSFORMER = "transformer", "Transformer Model"
    SKLEARN = "sklearn", "Scikit-learn Classifier"
    HYBRID = "hybrid", "Hybrid Model"


class TrainingStatus(models.TextChoices):
    """Training batch status"""

    QUEUED = "queued", "Queued"
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class DataSource(models.TextChoices):
    """Source of training data"""

    USER_FEEDBACK = "user_feedback", "User Feedback"
    MANUAL = "manual", "Manual Annotation"
    IMPORTED = "imported", "Imported Dataset"
    SYNTHETIC = "synthetic", "Synthetic Data"


class MLModel(models.Model):
    """
    ML model registry and metadata.

    Tracks trained models, their performance metrics, and deployment status.
    Supports model versioning and A/B testing.
    """

    # Model identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, help_text="Descriptive name for the model")
    model_type = models.CharField(max_length=50, choices=ModelType.choices)
    classification_types = models.JSONField(
        default=list,
        help_text="Classification types this model handles (PII, PHI, etc.)",
    )

    # Model files and configuration
    model_path = models.CharField(max_length=500, help_text="Path to model files")
    config = models.JSONField(
        default=dict,
        help_text="Model configuration parameters",
    )

    # Performance metrics
    accuracy = models.FloatField(null=True, blank=True, help_text="Overall accuracy (0-1)")
    precision = models.FloatField(null=True, blank=True, help_text="Precision score (0-1)")
    recall = models.FloatField(null=True, blank=True, help_text="Recall score (0-1)")
    f1_score = models.FloatField(null=True, blank=True, help_text="F1 score (0-1)")

    # Version control
    version = models.CharField(max_length=20, help_text="Model version (e.g., 1.0.0)")
    parent_model = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="child_models",
        help_text="Parent model if this is a fine-tuned version",
    )

    # Status and deployment
    is_active = models.BooleanField(default=False, help_text="Model is active and can be used")
    is_production = models.BooleanField(default=False, help_text="Model is deployed in production")

    # Training details
    training_samples = models.IntegerField(
        default=0,
        help_text="Number of samples used for training",
    )
    training_duration_seconds = models.FloatField(
        null=True,
        blank=True,
        help_text="Time taken to train the model",
    )
    training_params = models.JSONField(
        default=dict,
        help_text="Hyperparameters used during training",
    )

    # Timestamps
    trained_at = models.DateTimeField(auto_now_add=True)
    deployed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Metadata
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_ml_models",
    )

    class Meta:
        ordering = ["-trained_at"]
        indexes = [
            models.Index(fields=["model_type"]),
            models.Index(fields=["is_active", "is_production"]),
            models.Index(fields=["-trained_at"]),
        ]

    def __str__(self):
        return f"{self.name} v{self.version} ({self.get_model_type_display()})"

    @property
    def is_deployed(self):
        """Check if model is deployed"""
        return self.is_production and self.is_active


class TrainingDataset(models.Model):
    """
    Labeled training data for ML models.

    Stores text examples with entity annotations for training
    and fine-tuning classification models.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Text and annotations
    text = models.TextField(help_text="Raw text to classify")
    entities = models.JSONField(
        default=list,
        help_text='Entity annotations: [{"start": 0, "end": 5, "label": "PII"}]',
    )
    classification_type = models.CharField(
        max_length=50,
        help_text="Primary classification type (PII, PHI, etc.)",
    )

    # Metadata
    source = models.CharField(
        max_length=50,
        choices=DataSource.choices,
        help_text="Source of this training example",
    )
    language = models.CharField(
        max_length=10,
        default="en",
        help_text="Language code (ISO 639-1)",
    )

    # Quality control
    verified = models.BooleanField(
        default=False,
        help_text="Has been manually verified",
    )
    verified_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="verified_training_data",
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    # Training usage tracking
    used_in_training = models.BooleanField(
        default=False,
        help_text="Has been used in at least one training run",
    )
    last_used = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time this example was used in training",
    )
    times_used = models.IntegerField(
        default=0,
        help_text="Number of times used in training",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["classification_type"]),
            models.Index(fields=["source"]),
            models.Index(fields=["verified"]),
            models.Index(fields=["language"]),
        ]

    def __str__(self):
        return f"Training example: {self.text[:50]}... ({self.classification_type})"


class ClassificationFeedback(models.Model):
    """
    User feedback on classification results for active learning.

    Stores corrections and annotations from users to improve
    model accuracy over time.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Link to original classification
    classification_result = models.ForeignKey(
        "ClassificationResult",
        on_delete=models.CASCADE,
        related_name="feedback",
    )

    # Feedback details
    is_correct = models.BooleanField(help_text="Was the classification correct?")
    corrected_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Corrected classification type if wrong",
    )
    corrected_entities = models.JSONField(
        null=True,
        blank=True,
        help_text="Corrected entity annotations",
    )
    notes = models.TextField(blank=True, help_text="Additional notes or explanation")

    # User information
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="classification_feedback",
    )

    # Processing status
    incorporated_in_training = models.BooleanField(
        default=False,
        help_text="Feedback has been incorporated into training data",
    )
    training_batch = models.ForeignKey(
        "TrainingBatch",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="feedback_used",
        help_text="Training batch where this feedback was used",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When feedback was incorporated",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_correct"]),
            models.Index(fields=["incorporated_in_training"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        status = "Correct" if self.is_correct else "Incorrect"
        return f"Feedback: {status} from {self.user.username}"


class MLClassificationResult(models.Model):
    """
    Extended classification result with ML-specific metadata.

    Stores detailed information about ML-based classifications,
    including confidence scores, entity details, and processing metrics.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Link to base classification
    classification_result = models.OneToOneField(
        "ClassificationResult",
        on_delete=models.CASCADE,
        related_name="ml_result",
    )

    # Model used
    model = models.ForeignKey(
        MLModel,
        on_delete=models.PROTECT,
        related_name="classification_results",
    )

    # Detailed entity extraction
    entities = models.JSONField(
        default=list,
        help_text="Detailed entity extraction results",
    )

    # Separate regex and ML results for comparison
    regex_matches = models.JSONField(
        default=list,
        help_text="Entities found by regex patterns",
    )
    ml_matches = models.JSONField(
        default=list,
        help_text="Entities found by ML model",
    )

    # Confidence breakdown
    regex_confidence = models.FloatField(
        help_text="Confidence score from regex patterns (0-1)",
    )
    ml_confidence = models.FloatField(
        help_text="Confidence score from ML model (0-1)",
    )
    combined_confidence = models.FloatField(
        help_text="Final combined confidence score (0-1)",
    )

    # Performance metrics
    processing_time_ms = models.FloatField(
        help_text="Time taken to process (milliseconds)",
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["model"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return f"ML Result for {self.classification_result} (conf: {self.combined_confidence:.2f})"


class TrainingBatch(models.Model):
    """
    Tracks model training runs and their results.

    Records training parameters, metrics, and status for each
    training batch to enable monitoring and comparison.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Model being trained
    model = models.ForeignKey(
        MLModel,
        on_delete=models.CASCADE,
        related_name="training_batches",
    )

    # Training data split
    training_samples = models.IntegerField(help_text="Number of training samples")
    validation_samples = models.IntegerField(help_text="Number of validation samples")
    test_samples = models.IntegerField(help_text="Number of test samples")

    # Training status
    status = models.CharField(
        max_length=20,
        choices=TrainingStatus.choices,
        default=TrainingStatus.QUEUED,
    )

    # Training parameters
    epochs = models.IntegerField(default=10, help_text="Number of training epochs")
    batch_size = models.IntegerField(default=8, help_text="Training batch size")
    learning_rate = models.FloatField(default=0.001, help_text="Learning rate")
    hyperparameters = models.JSONField(
        default=dict,
        help_text="Additional hyperparameters",
    )

    # Performance metrics
    train_accuracy = models.FloatField(null=True, blank=True)
    val_accuracy = models.FloatField(null=True, blank=True)
    test_accuracy = models.FloatField(null=True, blank=True)
    train_loss = models.FloatField(null=True, blank=True)
    val_loss = models.FloatField(null=True, blank=True)

    # Timing information
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)

    # Logs and errors
    logs = models.TextField(blank=True, help_text="Training logs")
    error_message = models.TextField(blank=True, help_text="Error message if failed")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="training_batches",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["-created_at"]),
        ]
        verbose_name_plural = "Training batches"

    def __str__(self):
        return f"Training batch for {self.model.name} ({self.get_status_display()})"

    @property
    def is_complete(self):
        """Check if training is complete"""
        return self.status == TrainingStatus.COMPLETED

    @property
    def is_running(self):
        """Check if training is currently running"""
        return self.status == TrainingStatus.RUNNING


class ModelMetric(models.Model):
    """
    Time-series metrics for model performance tracking.

    Stores performance metrics over time to enable trending
    and performance degradation detection.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Model and timestamp
    model = models.ForeignKey(
        MLModel,
        on_delete=models.CASCADE,
        related_name="metrics",
    )
    recorded_at = models.DateTimeField(auto_now_add=True)

    # Metrics
    accuracy = models.FloatField()
    precision = models.FloatField()
    recall = models.FloatField()
    f1_score = models.FloatField()

    # Sample size
    sample_size = models.IntegerField(help_text="Number of samples evaluated")

    # Detailed metrics
    true_positives = models.IntegerField(default=0)
    false_positives = models.IntegerField(default=0)
    true_negatives = models.IntegerField(default=0)
    false_negatives = models.IntegerField(default=0)

    # Per-class metrics
    class_metrics = models.JSONField(
        default=dict,
        help_text="Metrics broken down by classification type",
    )

    class Meta:
        ordering = ["-recorded_at"]
        indexes = [
            models.Index(fields=["model", "-recorded_at"]),
        ]

    def __str__(self):
        return f"{self.model.name} metrics @ {self.recorded_at} (F1: {self.f1_score:.3f})"
