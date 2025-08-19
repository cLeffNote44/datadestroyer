import uuid

from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class MetricType(models.TextChoices):
    """Types of metrics we track"""

    STORAGE = "storage", _("Storage Usage")
    ACTIVITY = "activity", _("User Activity")
    SHARING = "sharing", _("Data Sharing")
    RETENTION = "retention", _("Data Retention")


class InsightType(models.TextChoices):
    """Types of insights we provide"""

    RISK = "risk", _("Privacy Risk")
    RECOMMENDATION = "recommendation", _("Recommendation")
    ALERT = "alert", _("Alert")
    TIP = "tip", _("Privacy Tip")


class SeverityLevel(models.TextChoices):
    """Severity levels for insights"""

    INFO = "info", _("Information")
    LOW = "low", _("Low")
    MEDIUM = "medium", _("Medium")
    HIGH = "high", _("High")
    CRITICAL = "critical", _("Critical")


class AnalyticsSnapshot(models.Model):
    """Daily snapshot of user analytics data"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="analytics_snapshots")
    date = models.DateField(help_text=_("Date of the snapshot"))

    # Core metrics
    total_documents = models.IntegerField(default=0)
    total_messages = models.IntegerField(default=0)
    total_forum_posts = models.IntegerField(default=0)
    storage_used_bytes = models.BigIntegerField(default=0)

    # Privacy and retention metrics
    retention_violations_count = models.IntegerField(
        default=0, help_text=_("Items past their intended retention date")
    )
    shared_documents_count = models.IntegerField(default=0)
    public_documents_count = models.IntegerField(default=0)
    encrypted_documents_count = models.IntegerField(default=0)

    # Moderation metrics
    total_content_scans = models.IntegerField(
        default=0, help_text=_("Total number of content scans performed")
    )
    content_violations_found = models.IntegerField(
        default=0, help_text=_("Total privacy violations detected")
    )
    critical_violations_count = models.IntegerField(
        default=0, help_text=_("Number of critical privacy violations")
    )
    avg_content_risk_score = models.FloatField(
        default=0.0, help_text=_("Average risk score of scanned content (0-100)")
    )
    quarantined_items_count = models.IntegerField(
        default=0, help_text=_("Number of items currently quarantined")
    )
    moderation_compliance_score = models.IntegerField(
        default=100,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("Content moderation compliance score"),
    )

    # Discovery system metrics
    total_data_assets = models.IntegerField(
        default=0, help_text=_("Total number of discovered data assets")
    )
    classified_assets_count = models.IntegerField(
        default=0, help_text=_("Number of assets with classification results")
    )
    sensitive_assets_count = models.IntegerField(
        default=0, help_text=_("Number of assets classified as sensitive (high/critical)")
    )
    discovery_insights_count = models.IntegerField(
        default=0, help_text=_("Number of active discovery insights")
    )
    avg_classification_confidence = models.FloatField(
        default=0.0, help_text=_("Average confidence score of classifications (0.0-1.0)")
    )
    data_lineage_relationships = models.IntegerField(
        default=0, help_text=_("Number of data lineage relationships tracked")
    )
    discovery_coverage_score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("Data discovery coverage score (0-100)"),
    )

    # Calculated scores (0-100)
    privacy_score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("Overall privacy score"),
    )
    security_score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("Security posture score"),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Analytics Snapshot")
        verbose_name_plural = _("Analytics Snapshots")
        unique_together = (("user", "date"),)
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["user", "date"]),
            models.Index(fields=["date", "privacy_score"]),
        ]

    def __str__(self):
        return f"Snapshot for {self.user.username} on {self.date}"

    @property
    def storage_used_mb(self) -> float:
        """Convert bytes to megabytes for display"""
        return round(self.storage_used_bytes / (1024 * 1024), 2)

    def calculate_privacy_score(self) -> int:
        """Calculate privacy score based on user's data patterns"""
        score = 100  # Start with perfect score

        # Deduct points for public documents
        if self.total_documents > 0:
            public_ratio = self.public_documents_count / self.total_documents
            score -= int(public_ratio * 30)  # Max 30 point penalty

        # Deduct points for unencrypted sensitive documents
        if self.total_documents > 0:
            encrypted_ratio = self.encrypted_documents_count / self.total_documents
            score -= int((1 - encrypted_ratio) * 25)  # Max 25 point penalty

        # Deduct points for retention violations
        score -= min(self.retention_violations_count * 5, 20)  # Max 20 point penalty

        # Deduct points for excessive sharing
        if self.total_documents > 0:
            shared_ratio = self.shared_documents_count / self.total_documents
            if shared_ratio > 0.5:  # More than 50% shared
                score -= int((shared_ratio - 0.5) * 50)  # Progressive penalty

        # Deduct points for content violations (NEW)
        score -= min(
            self.critical_violations_count * 10, 25
        )  # Max 25 point penalty for critical violations
        score -= min(
            self.content_violations_found * 2, 15
        )  # Max 15 point penalty for total violations

        # Deduct points based on content risk score (NEW)
        if self.avg_content_risk_score > 0:
            risk_penalty = int(self.avg_content_risk_score * 0.2)  # Max 20 point penalty
            score -= min(risk_penalty, 20)

        # Deduct points for quarantined items (NEW)
        score -= min(self.quarantined_items_count * 3, 10)  # Max 10 point penalty

        # Discovery system penalties (NEW)
        # Deduct points for sensitive assets that aren't properly managed
        if self.total_data_assets > 0:
            sensitive_ratio = self.sensitive_assets_count / self.total_data_assets
            if sensitive_ratio > 0.2:  # More than 20% sensitive
                score -= int((sensitive_ratio - 0.2) * 30)  # Progressive penalty
        
        # Deduct points for unclassified assets (lack of visibility)
        if self.total_data_assets > 0:
            classified_ratio = self.classified_assets_count / self.total_data_assets
            score -= int((1 - classified_ratio) * 15)  # Max 15 point penalty for poor classification coverage
        
        # Deduct points for low classification confidence
        if self.avg_classification_confidence > 0 and self.avg_classification_confidence < 0.7:
            confidence_penalty = int((0.7 - self.avg_classification_confidence) * 20)
            score -= min(confidence_penalty, 10)  # Max 10 point penalty
        
        # Deduct points for active discovery insights (unresolved issues)
        score -= min(self.discovery_insights_count * 2, 15)  # Max 15 point penalty

        return max(0, min(100, score))

    def calculate_moderation_compliance_score(self) -> int:
        """Calculate content moderation compliance score"""
        if self.total_content_scans == 0:
            return 100  # Perfect score if no scans performed yet

        score = 100

        # Calculate violation rate
        violation_rate = (
            (self.content_violations_found / self.total_content_scans)
            if self.total_content_scans > 0
            else 0
        )

        # Deduct points based on violation rate
        score -= int(violation_rate * 50)  # Up to 50 points for violation rate

        # Heavy penalty for critical violations
        if self.critical_violations_count > 0:
            score -= min(
                self.critical_violations_count * 15, 40
            )  # Up to 40 points for critical violations

        # Penalty for high average risk score
        if self.avg_content_risk_score > 40:
            risk_penalty = int((self.avg_content_risk_score - 40) * 0.5)
            score -= min(risk_penalty, 20)

        return max(0, min(100, score))


class DataUsageMetric(models.Model):
    """Tracks specific data usage patterns over time"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="usage_metrics")

    metric_type = models.CharField(max_length=20, choices=MetricType.choices)
    metric_name = models.CharField(max_length=100, help_text=_("Specific metric being tracked"))
    value = models.DecimalField(max_digits=15, decimal_places=2)
    unit = models.CharField(max_length=20, default="count", help_text=_("Unit of measurement"))

    timestamp = models.DateTimeField(default=timezone.now)
    metadata = models.JSONField(default=dict, blank=True, help_text=_("Additional metric context"))

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Data Usage Metric")
        verbose_name_plural = _("Data Usage Metrics")
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["user", "metric_type", "timestamp"]),
            models.Index(fields=["timestamp"]),
        ]

    def __str__(self):
        return f"{self.user.username}: {self.metric_name} = {self.value} {self.unit}"


class PrivacyInsight(models.Model):
    """Privacy recommendations and insights for users"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="privacy_insights")

    insight_type = models.CharField(max_length=20, choices=InsightType.choices)
    severity = models.CharField(
        max_length=20, choices=SeverityLevel.choices, default=SeverityLevel.INFO
    )

    title = models.CharField(max_length=255)
    description = models.TextField()
    action_text = models.CharField(
        max_length=100, blank=True, help_text=_("Call-to-action button text")
    )
    action_url = models.URLField(blank=True, help_text=_("URL for the recommended action"))

    # Tracking
    is_read = models.BooleanField(default=False)
    is_dismissed = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    dismissed_at = models.DateTimeField(null=True, blank=True)

    # Context data that generated this insight
    context_data = models.JSONField(default=dict, blank=True)

    # Lifecycle
    expires_at = models.DateTimeField(
        null=True, blank=True, help_text=_("When this insight becomes irrelevant")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Privacy Insight")
        verbose_name_plural = _("Privacy Insights")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read", "is_dismissed"]),
            models.Index(fields=["severity", "created_at"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        return f"{self.get_insight_type_display()}: {self.title}"

    def mark_as_read(self):
        """Mark insight as read by user"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at", "updated_at"])

    def dismiss(self):
        """Dismiss this insight"""
        self.is_dismissed = True
        self.dismissed_at = timezone.now()
        self.save(update_fields=["is_dismissed", "dismissed_at", "updated_at"])

    @property
    def is_expired(self) -> bool:
        """Check if insight has expired"""
        return self.expires_at and timezone.now() > self.expires_at


class RetentionTimeline(models.Model):
    """Tracks upcoming data deletions and retention events"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="retention_timeline")

    # What will be deleted
    item_type = models.CharField(
        max_length=50, help_text=_("Type of item (document, message, post)")
    )
    item_id = models.UUIDField(help_text=_("ID of the item to be deleted"))
    item_title = models.CharField(max_length=255, help_text=_("Human-readable item description"))

    # When and why
    scheduled_date = models.DateTimeField(help_text=_("When deletion is scheduled"))
    retention_reason = models.CharField(max_length=100, help_text=_("Reason for deletion"))
    can_extend = models.BooleanField(default=True, help_text=_("Whether user can extend retention"))

    # Status tracking
    is_notified = models.BooleanField(default=False)
    is_cancelled = models.BooleanField(default=False)
    is_completed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Retention Timeline Entry")
        verbose_name_plural = _("Retention Timeline Entries")
        ordering = ["scheduled_date"]
        indexes = [
            models.Index(fields=["user", "scheduled_date"]),
            models.Index(fields=["scheduled_date", "is_completed"]),
        ]

    def __str__(self):
        return f"{self.item_title} scheduled for deletion on {self.scheduled_date.date()}"
