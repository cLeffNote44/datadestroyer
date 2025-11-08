from typing import Dict, Optional

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

# Import ML models so Django can detect them
from .ml_models import (  # noqa: F401
    ClassificationFeedback,
    MLClassificationResult,
    MLModel,
    ModelMetric,
    TrainingBatch,
    TrainingDataset,
)

User = get_user_model()


class DataClassification(models.TextChoices):
    """Standard data classification categories"""

    PII = "pii", "Personally Identifiable Information"
    PHI = "phi", "Protected Health Information"
    FINANCIAL = "financial", "Financial Information"
    INTELLECTUAL_PROPERTY = "ip", "Intellectual Property"
    CONFIDENTIAL = "confidential", "Confidential Business Data"
    PUBLIC = "public", "Public Information"
    INTERNAL = "internal", "Internal Use Only"
    RESTRICTED = "restricted", "Restricted Access"


class SensitivityLevel(models.TextChoices):
    """Data sensitivity levels"""

    LOW = "low", "Low Sensitivity"
    MEDIUM = "medium", "Medium Sensitivity"
    HIGH = "high", "High Sensitivity"
    CRITICAL = "critical", "Critical Sensitivity"


class DiscoveryStatus(models.TextChoices):
    """Discovery job status"""

    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"


class ClassificationConfidence(models.TextChoices):
    """Classification confidence levels"""

    LOW = "low", "Low Confidence (< 60%)"
    MEDIUM = "medium", "Medium Confidence (60-80%)"
    HIGH = "high", "High Confidence (80-95%)"
    VERY_HIGH = "very_high", "Very High Confidence (> 95%)"


class DataAsset(models.Model):
    """Tracks discovered data assets across the system"""

    # Core identification
    name = models.CharField(max_length=255, help_text="Human-readable name for the data asset")
    description = models.TextField(blank=True, help_text="Detailed description of the data asset")

    # Generic foreign key to link to any model
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    # Data classification
    primary_classification = models.CharField(
        max_length=20, choices=DataClassification.choices, default=DataClassification.INTERNAL
    )
    secondary_classifications = models.JSONField(
        default=list, help_text="Additional classification categories"
    )
    sensitivity_level = models.CharField(
        max_length=10, choices=SensitivityLevel.choices, default=SensitivityLevel.MEDIUM
    )

    # Discovery metadata
    discovered_at = models.DateTimeField(auto_now_add=True)
    last_scanned = models.DateTimeField(auto_now=True)
    discovered_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="discovered_assets"
    )

    # Size and location information
    size_bytes = models.BigIntegerField(
        null=True, blank=True, help_text="Size in bytes if applicable"
    )
    file_path = models.CharField(
        max_length=1000, blank=True, help_text="File system path if applicable"
    )
    database_table = models.CharField(
        max_length=255, blank=True, help_text="Database table if applicable"
    )

    # Compliance and governance
    retention_policy = models.CharField(
        max_length=255, blank=True, help_text="Applicable retention policy"
    )
    compliance_tags = models.JSONField(
        default=list, help_text="Compliance framework tags (GDPR, HIPAA, etc.)"
    )
    access_level = models.CharField(max_length=50, blank=True, help_text="Required access level")

    # Tracking and metadata
    metadata = models.JSONField(default=dict, help_text="Additional custom metadata")
    is_active = models.BooleanField(
        default=True, help_text="Whether this asset is currently active"
    )

    class Meta:
        unique_together = ["content_type", "object_id"]
        indexes = [
            models.Index(fields=["primary_classification"]),
            models.Index(fields=["sensitivity_level"]),
            models.Index(fields=["discovered_at"]),
            models.Index(fields=["last_scanned"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_primary_classification_display()})"

    def get_classification_score(self) -> float:
        """Calculate overall classification risk score"""
        base_scores = {
            DataClassification.PUBLIC: 0.1,
            DataClassification.INTERNAL: 0.3,
            DataClassification.CONFIDENTIAL: 0.6,
            DataClassification.FINANCIAL: 0.8,
            DataClassification.PII: 0.9,
            DataClassification.PHI: 0.95,
            DataClassification.INTELLECTUAL_PROPERTY: 0.7,
            DataClassification.RESTRICTED: 1.0,
        }

        sensitivity_multipliers = {
            SensitivityLevel.LOW: 0.5,
            SensitivityLevel.MEDIUM: 0.75,
            SensitivityLevel.HIGH: 1.0,
            SensitivityLevel.CRITICAL: 1.25,
        }

        base_score = base_scores.get(self.primary_classification, 0.5)
        multiplier = sensitivity_multipliers.get(self.sensitivity_level, 1.0)

        return min(base_score * multiplier, 1.0)


class ClassificationRule(models.Model):
    """Rules for automatically classifying data"""

    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(help_text="Description of what this rule detects")

    # Rule configuration
    rule_type = models.CharField(
        max_length=20,
        choices=[
            ("regex", "Regular Expression"),
            ("keyword", "Keyword Matching"),
            ("ml_model", "Machine Learning Model"),
            ("context", "Context-based"),
            ("composite", "Composite Rule"),
        ],
        default="regex",
    )

    # Rule patterns and logic
    pattern = models.TextField(help_text="Pattern, keywords, or model configuration")
    confidence_threshold = models.FloatField(
        default=0.8, help_text="Minimum confidence required for classification"
    )

    # Classification output
    target_classification = models.CharField(max_length=20, choices=DataClassification.choices)
    target_sensitivity = models.CharField(max_length=10, choices=SensitivityLevel.choices)

    # Rule metadata
    priority = models.IntegerField(
        default=100, help_text="Rule priority (lower numbers = higher priority)"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="classification_rules"
    )

    # Performance tracking
    true_positives = models.IntegerField(default=0)
    false_positives = models.IntegerField(default=0)
    false_negatives = models.IntegerField(default=0)

    class Meta:
        ordering = ["priority", "name"]
        indexes = [
            models.Index(fields=["rule_type"]),
            models.Index(fields=["target_classification"]),
            models.Index(fields=["is_active", "priority"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_rule_type_display()})"

    def get_accuracy_metrics(self) -> Dict[str, float]:
        """Calculate rule accuracy metrics"""
        total_predictions = self.true_positives + self.false_positives + self.false_negatives

        if total_predictions == 0:
            return {"precision": 0.0, "recall": 0.0, "f1_score": 0.0}

        precision = (
            self.true_positives / (self.true_positives + self.false_positives)
            if (self.true_positives + self.false_positives) > 0
            else 0.0
        )
        recall = (
            self.true_positives / (self.true_positives + self.false_negatives)
            if (self.true_positives + self.false_negatives) > 0
            else 0.0
        )
        f1_score = (
            2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        )

        return {"precision": precision, "recall": recall, "f1_score": f1_score}


class DataLineage(models.Model):
    """Tracks data flow and relationships between assets"""

    source_asset = models.ForeignKey(
        DataAsset, on_delete=models.CASCADE, related_name="downstream_lineages"
    )
    target_asset = models.ForeignKey(
        DataAsset, on_delete=models.CASCADE, related_name="upstream_lineages"
    )

    # Relationship details
    relationship_type = models.CharField(
        max_length=20,
        choices=[
            ("copy", "Direct Copy"),
            ("transform", "Transformation"),
            ("aggregate", "Aggregation"),
            ("join", "Data Join"),
            ("filter", "Filtered View"),
            ("derive", "Derived Data"),
            ("reference", "Reference Link"),
        ],
        default="copy",
    )

    transformation_logic = models.TextField(
        blank=True, help_text="Description of how data is transformed"
    )

    # Tracking information
    created_at = models.DateTimeField(auto_now_add=True)
    last_verified = models.DateTimeField(auto_now=True)
    confidence_score = models.FloatField(
        default=1.0, help_text="Confidence in this lineage relationship (0.0-1.0)"
    )

    # Impact analysis
    impact_score = models.FloatField(
        default=0.5, help_text="Impact score if source changes (0.0-1.0)"
    )

    class Meta:
        unique_together = ["source_asset", "target_asset"]
        indexes = [
            models.Index(fields=["relationship_type"]),
            models.Index(fields=["confidence_score"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.source_asset.name} → {self.target_asset.name} ({self.get_relationship_type_display()})"


class DiscoveryJob(models.Model):
    """Manages data discovery scanning jobs"""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Job configuration
    job_type = models.CharField(
        max_length=20,
        choices=[
            ("full_scan", "Full System Scan"),
            ("incremental", "Incremental Scan"),
            ("targeted", "Targeted Scan"),
            ("scheduled", "Scheduled Scan"),
            ("real_time", "Real-time Monitoring"),
        ],
        default="full_scan",
    )

    # Scope configuration
    target_apps = models.JSONField(default=list, help_text="Django apps to scan (empty = all apps)")
    target_models = models.JSONField(
        default=list, help_text="Specific models to scan (empty = all models)"
    )
    target_paths = models.JSONField(default=list, help_text="File system paths to scan")

    # Classification rules to apply
    classification_rules = models.ManyToManyField(
        ClassificationRule, blank=True, help_text="Rules to apply during discovery"
    )

    # Scheduling
    schedule_cron = models.CharField(
        max_length=100, blank=True, help_text="Cron expression for scheduled jobs"
    )
    is_scheduled = models.BooleanField(default=False)

    # Execution tracking
    status = models.CharField(
        max_length=20, choices=DiscoveryStatus.choices, default=DiscoveryStatus.PENDING
    )

    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="discovery_jobs")

    # Results tracking
    assets_discovered = models.IntegerField(default=0)
    assets_classified = models.IntegerField(default=0)
    errors_encountered = models.IntegerField(default=0)

    # Configuration and results
    configuration = models.JSONField(
        default=dict, help_text="Job-specific configuration parameters"
    )
    results_summary = models.JSONField(default=dict, help_text="Summary of job results")
    error_log = models.TextField(blank=True, help_text="Error messages and debugging info")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["job_type"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["is_scheduled"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    def get_duration(self) -> Optional[float]:
        """Get job duration in seconds"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def get_discovery_rate(self) -> float:
        """Get assets discovered per minute"""
        duration = self.get_duration()
        if duration and duration > 0:
            return (self.assets_discovered * 60) / duration
        return 0.0


class ClassificationResult(models.Model):
    """Stores results of data classification"""

    data_asset = models.ForeignKey(
        DataAsset, on_delete=models.CASCADE, related_name="classification_results"
    )
    classification_rule = models.ForeignKey(
        ClassificationRule, on_delete=models.CASCADE, related_name="classification_results"
    )
    discovery_job = models.ForeignKey(
        DiscoveryJob,
        on_delete=models.CASCADE,
        related_name="classification_results",
        null=True,
        blank=True,
    )

    # Classification output
    predicted_classification = models.CharField(max_length=20, choices=DataClassification.choices)
    predicted_sensitivity = models.CharField(max_length=10, choices=SensitivityLevel.choices)
    confidence_score = models.FloatField(help_text="Confidence in this classification (0.0-1.0)")
    confidence_level = models.CharField(max_length=10, choices=ClassificationConfidence.choices)

    # Detailed results
    matched_patterns = models.JSONField(default=list, help_text="Specific patterns that matched")
    context_information = models.JSONField(
        default=dict, help_text="Additional context used in classification"
    )

    # Validation and feedback
    is_validated = models.BooleanField(default=False)
    is_correct = models.BooleanField(
        null=True, blank=True, help_text="Human validation of correctness"
    )
    validated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="validated_classifications",
    )
    validated_at = models.DateTimeField(null=True, blank=True)

    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["data_asset", "classification_rule"]
        indexes = [
            models.Index(fields=["predicted_classification"]),
            models.Index(fields=["confidence_score"]),
            models.Index(fields=["is_validated"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.data_asset.name} → {self.get_predicted_classification_display()} ({self.confidence_score:.2%})"


class DataDiscoveryInsight(models.Model):
    """Insights generated from data discovery analysis"""

    title = models.CharField(max_length=255)
    description = models.TextField()

    insight_type = models.CharField(
        max_length=20,
        choices=[
            ("classification", "Classification Pattern"),
            ("compliance", "Compliance Issue"),
            ("security", "Security Risk"),
            ("governance", "Governance Recommendation"),
            ("performance", "Performance Insight"),
            ("quality", "Data Quality Issue"),
        ],
        default="classification",
    )

    severity = models.CharField(
        max_length=10,
        choices=[
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
            ("critical", "Critical"),
        ],
        default="medium",
    )

    # Related data
    related_assets = models.ManyToManyField(DataAsset, blank=True)
    related_jobs = models.ManyToManyField(DiscoveryJob, blank=True)

    # Insight data
    insight_data = models.JSONField(
        default=dict, help_text="Structured data supporting the insight"
    )

    # Recommendations
    recommendations = models.JSONField(default=list, help_text="Actionable recommendations")

    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="resolved_insights"
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["insight_type"]),
            models.Index(fields=["severity"]),
            models.Index(fields=["is_resolved"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_severity_display()})"


class RealTimeMonitor(models.Model):
    """Configuration for real-time data monitoring"""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Monitoring configuration
    monitor_type = models.CharField(
        max_length=20,
        choices=[
            ("filesystem", "File System Changes"),
            ("database", "Database Changes"),
            ("api", "API Traffic"),
            ("upload", "File Uploads"),
            ("model_changes", "Model Instance Changes"),
        ],
        default="model_changes",
    )

    # Target specification
    target_specification = models.JSONField(
        default=dict, help_text="Configuration for what to monitor"
    )

    # Classification settings
    auto_classify = models.BooleanField(default=True)
    classification_rules = models.ManyToManyField(ClassificationRule, blank=True)

    # Alert configuration
    alert_on_sensitive = models.BooleanField(default=True)
    alert_threshold = models.CharField(
        max_length=10, choices=SensitivityLevel.choices, default=SensitivityLevel.HIGH
    )

    # Notification settings
    notification_users = models.ManyToManyField(
        User, blank=True, related_name="monitoring_notifications"
    )
    notification_email = models.EmailField(blank=True)

    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="real_time_monitors"
    )

    # Performance tracking
    items_monitored = models.IntegerField(default=0)
    alerts_generated = models.IntegerField(default=0)
    last_activity = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["monitor_type"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_monitor_type_display()})"


class MonitoringEvent(models.Model):
    """Events captured by real-time monitoring"""

    monitor = models.ForeignKey(
        RealTimeMonitor, on_delete=models.CASCADE, related_name="monitoring_events"
    )

    # Event details
    event_type = models.CharField(max_length=50)
    event_data = models.JSONField(default=dict)

    # Related asset (if classified)
    data_asset = models.ForeignKey(
        DataAsset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="monitoring_events",
    )

    # Classification results
    was_classified = models.BooleanField(default=False)
    triggered_alert = models.BooleanField(default=False)

    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event_type"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["triggered_alert"]),
        ]

    def __str__(self):
        return f"{self.monitor.name}: {self.event_type} at {self.created_at}"
