import uuid
from typing import Optional

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class Severity(models.TextChoices):
    LOW = "low", _("Low")
    MEDIUM = "medium", _("Medium")
    HIGH = "high", _("High")
    CRITICAL = "critical", _("Critical")


class DeletionStatus(models.TextChoices):
    REQUESTED = "requested", _("Requested")
    APPROVED = "approved", _("Approved")
    SCHEDULED = "scheduled", _("Scheduled")
    IN_PROGRESS = "in_progress", _("In progress")
    COMPLETED = "completed", _("Completed")
    FAILED = "failed", _("Failed")
    CANCELED = "canceled", _("Canceled")


class DeletionTarget(models.TextChoices):
    DOCUMENT = "document", _("Single document")
    USER_ALL_DATA = "user_all_data", _("All data for a user")
    CATEGORY = "category", _("All documents in a category for a user")


class RetentionPolicy(models.Model):
    """Reusable retention rules. Can be global or scoped to a user or category."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    days = models.PositiveIntegerField(default=90)

    # Optional scoping
    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.CASCADE, related_name="retention_policies"
    )
    category = models.ForeignKey(
        "documents.DocumentCategory",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="retention_policies",
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Retention Policy")
        verbose_name_plural = _("Retention Policies")
        indexes = [
            models.Index(fields=["is_active"]),
            models.Index(fields=["user", "category"]),
        ]

    def __str__(self):
        scope = "global"
        if self.user:
            scope = f"user:{self.user_id}"
        if self.category:
            scope += f"/cat:{self.category_id}"
        return f"{self.name} ({scope}, {self.days}d)"


class DeletionRequest(models.Model):
    """Tracks deletion requests for documents or user data."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="deletion_requests")

    target = models.CharField(max_length=20, choices=DeletionTarget.choices)
    document = models.ForeignKey(
        "documents.Document",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="deletion_requests",
    )
    category = models.ForeignKey(
        "documents.DocumentCategory",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="category_deletion_requests",
    )

    reason = models.CharField(max_length=255, blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=20, choices=DeletionStatus.choices, default=DeletionStatus.REQUESTED
    )
    failure_reason = models.TextField(blank=True)

    retention_policy = models.ForeignKey(
        RetentionPolicy,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="deletion_requests",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Deletion Request")
        verbose_name_plural = _("Deletion Requests")
        ordering = ["-requested_at"]
        indexes = [
            models.Index(fields=["status", "scheduled_for"]),
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self):
        return f"DeletionRequest({self.id}, {self.target}, {self.status})"

    def approve(self, schedule_time: Optional[timezone.datetime] = None):
        self.status = DeletionStatus.APPROVED
        self.approved_at = timezone.now()
        self.scheduled_for = schedule_time or (
            timezone.now()
            + timezone.timedelta(days=self.retention_policy.days if self.retention_policy else 0)
        )
        self.save(update_fields=["status", "approved_at", "scheduled_for", "updated_at"])


class PurgeJobStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    RUNNING = "running", _("Running")
    COMPLETED = "completed", _("Completed")
    FAILED = "failed", _("Failed")


class PurgeJob(models.Model):
    """Represents a batch purge execution."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    triggered_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="triggered_purge_jobs"
    )
    status = models.CharField(
        max_length=20, choices=PurgeJobStatus.choices, default=PurgeJobStatus.PENDING
    )
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    items_total = models.PositiveIntegerField(default=0)
    items_succeeded = models.PositiveIntegerField(default=0)
    items_failed = models.PositiveIntegerField(default=0)

    log = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Purge Job")
        verbose_name_plural = _("Purge Jobs")
        ordering = ["-created_at"]

    def __str__(self):
        return f"PurgeJob({self.id}, {self.status})"


class ExposureIncident(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reporter = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="reported_incidents"
    )
    impacted_user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="incidents"
    )

    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.LOW)
    description = models.TextField()
    impacted_documents = models.ManyToManyField(
        "documents.Document", blank=True, related_name="incidents"
    )

    detected_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Exposure Incident")
        verbose_name_plural = _("Exposure Incidents")
        ordering = ["-detected_at"]

    def __str__(self):
        return f"Incident({self.severity}) for user {self.impacted_user_id}"


class DataExportStatus(models.TextChoices):
    REQUESTED = "requested", _("Requested")
    PROCESSING = "processing", _("Processing")
    READY = "ready", _("Ready")
    EXPIRED = "expired", _("Expired")
    FAILED = "failed", _("Failed")


class DataExportRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="data_exports")
    status = models.CharField(
        max_length=20, choices=DataExportStatus.choices, default=DataExportStatus.REQUESTED
    )

    requested_at = models.DateTimeField(auto_now_add=True)
    fulfilled_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    download_url = models.URLField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = _("Data Export Request")
        verbose_name_plural = _("Data Export Requests")
        ordering = ["-requested_at"]

    def __str__(self):
        return f"ExportRequest({self.user_id}, {self.status})"
