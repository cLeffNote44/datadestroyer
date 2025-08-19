import re
import uuid
from datetime import timedelta
from typing import List

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class SensitivityLevel(models.TextChoices):
    """Sensitivity levels for content detection"""

    LOW = "low", _("Low")
    MEDIUM = "medium", _("Medium")
    HIGH = "high", _("High")
    CRITICAL = "critical", _("Critical")


class ViolationType(models.TextChoices):
    """Types of policy violations"""

    PII_DETECTED = "pii_detected", _("Personal Identifiable Information")
    FINANCIAL_DATA = "financial_data", _("Financial Information")
    MEDICAL_DATA = "medical_data", _("Medical Information")
    LEGAL_DATA = "legal_data", _("Legal Information")
    CUSTOM_PATTERN = "custom_pattern", _("Custom Sensitive Pattern")
    BULK_SHARING = "bulk_sharing", _("Bulk Sensitive Data Sharing")


class ModerationStatus(models.TextChoices):
    """Content moderation status"""

    PENDING = "pending", _("Pending Review")
    APPROVED = "approved", _("Approved")
    QUARANTINED = "quarantined", _("Quarantined")
    BLOCKED = "blocked", _("Blocked")
    REQUIRES_REVIEW = "requires_review", _("Requires Manual Review")


class ActionType(models.TextChoices):
    """Types of automated moderation actions"""

    SCAN = "scan", _("Content Scanned")
    QUARANTINE = "quarantine", _("Content Quarantined")
    NOTIFY_USER = "notify_user", _("User Notified")
    BLOCK_SHARING = "block_sharing", _("Sharing Blocked")
    REQUIRE_REVIEW = "require_review", _("Manual Review Required")
    APPROVE = "approve", _("Content Approved")
    RELEASE = "release", _("Content Released")


class SensitiveContentPattern(models.Model):
    """Configurable patterns for detecting sensitive content"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, help_text=_("Human-readable pattern name"))
    pattern_type = models.CharField(max_length=20, choices=ViolationType.choices)
    regex_pattern = models.TextField(help_text=_("Regular expression pattern"))
    description = models.TextField(blank=True)

    sensitivity_level = models.CharField(
        max_length=10, choices=SensitivityLevel.choices, default=SensitivityLevel.MEDIUM
    )

    is_active = models.BooleanField(default=True)
    auto_quarantine = models.BooleanField(
        default=False, help_text=_("Automatically quarantine content matching this pattern")
    )

    # Pattern configuration
    case_sensitive = models.BooleanField(default=False)
    match_whole_words = models.BooleanField(default=True)
    minimum_matches = models.IntegerField(
        default=1, help_text=_("Minimum number of matches to trigger violation")
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Sensitive Content Pattern")
        verbose_name_plural = _("Sensitive Content Patterns")
        ordering = ["-sensitivity_level", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_sensitivity_level_display()})"

    def clean(self):
        """Validate regex pattern"""
        try:
            re.compile(self.regex_pattern)
        except re.error as e:
            raise ValidationError({"regex_pattern": f"Invalid regex pattern: {e}"})

    def test_content(self, content: str) -> List[str]:
        """Test content against this pattern and return matches"""
        flags = 0 if self.case_sensitive else re.IGNORECASE

        if self.match_whole_words:
            pattern = r"\b" + self.regex_pattern + r"\b"
        else:
            pattern = self.regex_pattern

        try:
            matches = re.findall(pattern, content, flags)
            return matches if len(matches) >= self.minimum_matches else []
        except re.error:
            return []


class ContentScan(models.Model):
    """Records of content scanning operations"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Generic foreign key to any content type (Document, Message, Post, etc.)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=255)
    content_object = GenericForeignKey("content_type", "object_id")

    # Scan metadata
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="content_scans")
    scan_type = models.CharField(
        max_length=20,
        choices=[
            ("manual", _("Manual Scan")),
            ("automatic", _("Automatic Scan")),
            ("bulk", _("Bulk Scan")),
            ("scheduled", _("Scheduled Scan")),
        ],
        default="automatic",
    )

    # Scan results
    violations_found = models.IntegerField(default=0)
    highest_severity = models.CharField(
        max_length=10, choices=SensitivityLevel.choices, null=True, blank=True
    )
    scan_score = models.IntegerField(
        default=0, help_text=_("Risk score from 0 (safe) to 100 (high risk)")
    )

    # Processing info
    content_length = models.IntegerField(help_text=_("Length of scanned content in characters"))
    processing_time_ms = models.IntegerField(help_text=_("Processing time in milliseconds"))
    patterns_matched = models.JSONField(
        default=list, help_text=_("List of pattern IDs that matched")
    )

    # Status and metadata
    scan_status = models.CharField(
        max_length=20,
        choices=[("completed", _("Completed")), ("failed", _("Failed")), ("partial", _("Partial"))],
        default="completed",
    )
    error_message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    scanned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Content Scan")
        verbose_name_plural = _("Content Scans")
        ordering = ["-scanned_at"]
        indexes = [
            models.Index(fields=["user", "scanned_at"]),
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["highest_severity", "scanned_at"]),
        ]

    def __str__(self):
        return f"Scan of {self.content_type.name} - {self.violations_found} violations"

    @property
    def risk_level(self) -> str:
        """Calculate human-readable risk level from scan score"""
        if self.scan_score >= 80:
            return "Critical"
        elif self.scan_score >= 60:
            return "High"
        elif self.scan_score >= 40:
            return "Medium"
        elif self.scan_score >= 20:
            return "Low"
        else:
            return "Minimal"


class PolicyViolation(models.Model):
    """Individual policy violations found during content scanning"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content_scan = models.ForeignKey(
        ContentScan, on_delete=models.CASCADE, related_name="violations"
    )
    pattern = models.ForeignKey(
        SensitiveContentPattern, on_delete=models.CASCADE, related_name="violations"
    )

    # Violation details
    violation_type = models.CharField(max_length=20, choices=ViolationType.choices)
    severity = models.CharField(max_length=10, choices=SensitivityLevel.choices)

    # Match details
    matched_content = models.TextField(
        help_text=_("The actual content that matched (may be redacted)")
    )
    match_count = models.IntegerField(default=1)
    context_snippet = models.TextField(
        blank=True, help_text=_("Surrounding context (with sensitive data redacted)")
    )

    # Position information
    start_position = models.IntegerField(null=True, blank=True)
    end_position = models.IntegerField(null=True, blank=True)
    line_number = models.IntegerField(null=True, blank=True)

    # Resolution status
    is_resolved = models.BooleanField(default=False)
    resolution_action = models.CharField(
        max_length=50,
        choices=[
            ("user_acknowledged", _("User Acknowledged")),
            ("content_modified", _("Content Modified")),
            ("false_positive", _("Marked as False Positive")),
            ("approved_exception", _("Approved Exception")),
            ("content_removed", _("Content Removed")),
        ],
        blank=True,
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="resolved_violations"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Policy Violation")
        verbose_name_plural = _("Policy Violations")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["content_scan", "severity"]),
            models.Index(fields=["violation_type", "created_at"]),
            models.Index(fields=["is_resolved", "severity"]),
        ]

    def __str__(self):
        return f"{self.get_violation_type_display()} - {self.get_severity_display()}"

    def resolve(self, action: str, resolved_by: User, notes: str = ""):
        """Mark violation as resolved with specified action"""
        self.is_resolved = True
        self.resolution_action = action
        self.resolved_by = resolved_by
        self.resolved_at = timezone.now()
        if notes:
            if "resolution_notes" not in self.content_scan.metadata:
                self.content_scan.metadata["resolution_notes"] = []
            self.content_scan.metadata["resolution_notes"].append(
                {
                    "violation_id": str(self.id),
                    "notes": notes,
                    "resolved_at": timezone.now().isoformat(),
                }
            )
            self.content_scan.save()
        self.save()


class ModerationAction(models.Model):
    """Automated and manual moderation actions taken on content"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Related to either a content scan or a specific violation
    content_scan = models.ForeignKey(
        ContentScan, on_delete=models.CASCADE, related_name="moderation_actions"
    )
    violation = models.ForeignKey(
        PolicyViolation, on_delete=models.CASCADE, null=True, blank=True, related_name="actions"
    )

    action_type = models.CharField(max_length=20, choices=ActionType.choices)
    action_status = models.CharField(
        max_length=20, choices=ModerationStatus.choices, default=ModerationStatus.PENDING
    )

    # Action details
    reason = models.TextField(help_text=_("Reason for taking this action"))
    automated = models.BooleanField(
        default=True, help_text=_("Whether action was automated or manual")
    )

    # User and admin references
    triggered_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="triggered_moderation_actions"
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_moderation_actions",
    )

    # Action configuration
    expiry_date = models.DateTimeField(
        null=True, blank=True, help_text=_("When this action expires (e.g., quarantine period)")
    )
    notification_sent = models.BooleanField(default=False)
    user_acknowledged = models.BooleanField(default=False)

    # Metadata
    action_data = models.JSONField(
        default=dict, help_text=_("Additional data specific to this action type")
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Moderation Action")
        verbose_name_plural = _("Moderation Actions")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["action_type", "action_status"]),
            models.Index(fields=["triggered_by", "created_at"]),
            models.Index(fields=["expiry_date"]),
        ]

    def __str__(self):
        return f"{self.get_action_type_display()} - {self.get_action_status_display()}"

    @property
    def is_expired(self) -> bool:
        """Check if this action has expired"""
        return self.expiry_date and timezone.now() > self.expiry_date

    def extend_expiry(self, days: int) -> None:
        """Extend the expiry date by specified number of days"""
        if self.expiry_date:
            self.expiry_date += timedelta(days=days)
        else:
            self.expiry_date = timezone.now() + timedelta(days=days)
        self.save()


class ModerationSettings(models.Model):
    """Per-user moderation settings and preferences"""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="moderation_settings")

    # Scanning preferences
    auto_scan_enabled = models.BooleanField(
        default=True, help_text=_("Automatically scan new content")
    )
    scan_sensitivity = models.CharField(
        max_length=10,
        choices=SensitivityLevel.choices,
        default=SensitivityLevel.MEDIUM,
        help_text=_("Minimum sensitivity level to trigger notifications"),
    )

    # Notification preferences
    notify_on_violations = models.BooleanField(
        default=True, help_text=_("Send notifications when violations are found")
    )
    notify_on_quarantine = models.BooleanField(
        default=True, help_text=_("Send notifications when content is quarantined")
    )
    email_notifications = models.BooleanField(
        default=False, help_text=_("Send email notifications for moderation events")
    )

    # Auto-action settings
    auto_quarantine_critical = models.BooleanField(
        default=False, help_text=_("Automatically quarantine critical violations")
    )
    auto_block_sharing = models.BooleanField(
        default=True, help_text=_("Block sharing of content with violations")
    )

    # Custom patterns
    custom_sensitive_terms = models.JSONField(
        default=list, blank=True, help_text=_("User-defined sensitive terms to watch for")
    )

    # Exemptions
    trusted_domains = models.JSONField(
        default=list,
        blank=True,
        help_text=_("Domains that are trusted for sharing sensitive content"),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Moderation Settings")
        verbose_name_plural = _("Moderation Settings")

    def __str__(self):
        return f"Moderation settings for {self.user.username}"
