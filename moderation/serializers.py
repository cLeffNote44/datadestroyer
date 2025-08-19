"""
Django REST Framework serializers for content moderation system.

Provides serialization for:
- Content scanning operations
- Policy violation management
- Moderation actions and workflows
- Pattern management
- User settings
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import (
    ContentScan,
    ModerationAction,
    ModerationSettings,
    PolicyViolation,
    SensitiveContentPattern,
    SensitivityLevel,
)

User = get_user_model()


class SensitiveContentPatternSerializer(serializers.ModelSerializer):
    """Serializer for sensitive content patterns"""

    class Meta:
        model = SensitiveContentPattern
        fields = [
            "id",
            "name",
            "pattern_type",
            "regex_pattern",
            "description",
            "sensitivity_level",
            "is_active",
            "auto_quarantine",
            "case_sensitive",
            "match_whole_words",
            "minimum_matches",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_regex_pattern(self, value):
        """Validate regex pattern"""
        import re

        try:
            re.compile(value)
            return value
        except re.error as e:
            raise serializers.ValidationError(f"Invalid regex pattern: {e}")


class PolicyViolationSerializer(serializers.ModelSerializer):
    """Serializer for policy violations"""

    pattern_name = serializers.CharField(source="pattern.name", read_only=True)
    violation_type_display = serializers.CharField(
        source="get_violation_type_display", read_only=True
    )
    severity_display = serializers.CharField(source="get_severity_display", read_only=True)
    resolution_action_display = serializers.CharField(
        source="get_resolution_action_display", read_only=True
    )
    resolved_by_username = serializers.CharField(source="resolved_by.username", read_only=True)

    class Meta:
        model = PolicyViolation
        fields = [
            "id",
            "violation_type",
            "violation_type_display",
            "severity",
            "severity_display",
            "matched_content",
            "match_count",
            "context_snippet",
            "start_position",
            "end_position",
            "line_number",
            "is_resolved",
            "resolution_action",
            "resolution_action_display",
            "resolved_at",
            "resolved_by_username",
            "pattern_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "violation_type_display",
            "severity_display",
            "resolution_action_display",
            "resolved_by_username",
            "pattern_name",
            "created_at",
            "updated_at",
        ]


class ContentScanSerializer(serializers.ModelSerializer):
    """Serializer for content scans"""

    violations = PolicyViolationSerializer(many=True, read_only=True)
    scan_type_display = serializers.CharField(source="get_scan_type_display", read_only=True)
    highest_severity_display = serializers.CharField(
        source="get_highest_severity_display", read_only=True
    )
    risk_level = serializers.CharField(read_only=True)
    user_username = serializers.CharField(source="user.username", read_only=True)
    content_type_name = serializers.CharField(source="content_type.name", read_only=True)

    class Meta:
        model = ContentScan
        fields = [
            "id",
            "content_type_name",
            "object_id",
            "user_username",
            "scan_type",
            "scan_type_display",
            "violations_found",
            "highest_severity",
            "highest_severity_display",
            "scan_score",
            "risk_level",
            "content_length",
            "processing_time_ms",
            "patterns_matched",
            "scan_status",
            "error_message",
            "metadata",
            "scanned_at",
            "violations",
        ]
        read_only_fields = [
            "id",
            "scan_type_display",
            "highest_severity_display",
            "risk_level",
            "user_username",
            "content_type_name",
            "scanned_at",
            "violations",
        ]


class ModerationActionSerializer(serializers.ModelSerializer):
    """Serializer for moderation actions"""

    action_type_display = serializers.CharField(source="get_action_type_display", read_only=True)
    action_status_display = serializers.CharField(
        source="get_action_status_display", read_only=True
    )
    triggered_by_username = serializers.CharField(source="triggered_by.username", read_only=True)
    reviewed_by_username = serializers.CharField(source="reviewed_by.username", read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = ModerationAction
        fields = [
            "id",
            "action_type",
            "action_type_display",
            "action_status",
            "action_status_display",
            "reason",
            "automated",
            "triggered_by_username",
            "reviewed_by_username",
            "expiry_date",
            "is_expired",
            "notification_sent",
            "user_acknowledged",
            "action_data",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "action_type_display",
            "action_status_display",
            "triggered_by_username",
            "reviewed_by_username",
            "is_expired",
            "created_at",
            "updated_at",
        ]


class ModerationSettingsSerializer(serializers.ModelSerializer):
    """Serializer for user moderation settings"""

    user_username = serializers.CharField(source="user.username", read_only=True)
    scan_sensitivity_display = serializers.CharField(
        source="get_scan_sensitivity_display", read_only=True
    )

    class Meta:
        model = ModerationSettings
        fields = [
            "user_username",
            "auto_scan_enabled",
            "scan_sensitivity",
            "scan_sensitivity_display",
            "notify_on_violations",
            "notify_on_quarantine",
            "email_notifications",
            "auto_quarantine_critical",
            "auto_block_sharing",
            "custom_sensitive_terms",
            "trusted_domains",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["user_username", "scan_sensitivity_display", "created_at", "updated_at"]


# API Request/Response Serializers


class ContentScanRequestSerializer(serializers.Serializer):
    """Serializer for content scanning API requests"""

    content = serializers.CharField(help_text="Content text to scan")
    content_type = serializers.CharField(
        required=False, help_text="Content type identifier (e.g., 'document', 'message', 'post')"
    )
    object_id = serializers.CharField(
        required=False, help_text="ID of the content object being scanned"
    )
    scan_type = serializers.ChoiceField(
        choices=[("manual", "Manual"), ("automatic", "Automatic"), ("bulk", "Bulk")],
        default="manual",
        help_text="Type of scan being performed",
    )
    user_sensitivity = serializers.ChoiceField(
        choices=SensitivityLevel.choices,
        default=SensitivityLevel.MEDIUM,
        required=False,
        help_text="Sensitivity level for scanning",
    )


class ContentScanResponseSerializer(serializers.Serializer):
    """Serializer for content scanning API responses"""

    scan_id = serializers.UUIDField(read_only=True)
    status = serializers.CharField(read_only=True)
    violations_found = serializers.IntegerField(read_only=True)
    scan_score = serializers.IntegerField(read_only=True)
    risk_level = serializers.CharField(read_only=True)
    processing_time_ms = serializers.IntegerField(read_only=True)
    recommended_actions = serializers.ListField(read_only=True)
    violations = PolicyViolationSerializer(many=True, read_only=True)


class BulkScanRequestSerializer(serializers.Serializer):
    """Serializer for bulk scanning requests"""

    content_items = serializers.ListField(
        child=serializers.DictField(), help_text="List of content items to scan"
    )
    scan_type = serializers.ChoiceField(
        choices=[("bulk", "Bulk"), ("scheduled", "Scheduled")], default="bulk"
    )

    def validate_content_items(self, value):
        """Validate content items structure"""
        if len(value) > 100:  # Limit bulk operations
            raise serializers.ValidationError("Maximum 100 items allowed per bulk request")

        for item in value:
            if "content" not in item:
                raise serializers.ValidationError("Each item must have 'content' field")

        return value


class QuarantineActionSerializer(serializers.Serializer):
    """Serializer for quarantine action requests"""

    scan_ids = serializers.ListField(
        child=serializers.UUIDField(), help_text="List of scan IDs to quarantine"
    )
    reason = serializers.CharField(max_length=500, help_text="Reason for quarantine action")
    expiry_days = serializers.IntegerField(
        default=7, min_value=1, max_value=365, help_text="Number of days until quarantine expires"
    )


class ViolationResolutionSerializer(serializers.Serializer):
    """Serializer for resolving policy violations"""

    violation_id = serializers.UUIDField()
    action = serializers.ChoiceField(
        choices=[
            ("user_acknowledged", "User Acknowledged"),
            ("content_modified", "Content Modified"),
            ("false_positive", "False Positive"),
            ("approved_exception", "Approved Exception"),
            ("content_removed", "Content Removed"),
        ]
    )
    notes = serializers.CharField(
        max_length=1000, required=False, help_text="Additional notes about resolution"
    )


class ModerationDashboardSerializer(serializers.Serializer):
    """Serializer for moderation dashboard data"""

    total_scans = serializers.IntegerField(read_only=True)
    recent_violations = serializers.IntegerField(read_only=True)
    high_risk_content = serializers.IntegerField(read_only=True)
    quarantined_items = serializers.IntegerField(read_only=True)
    pending_reviews = serializers.IntegerField(read_only=True)

    violation_trends = serializers.ListField(read_only=True)
    risk_distribution = serializers.DictField(read_only=True)
    top_violation_types = serializers.ListField(read_only=True)

    recent_scans = ContentScanSerializer(many=True, read_only=True)
    critical_violations = PolicyViolationSerializer(many=True, read_only=True)


class PatternTestSerializer(serializers.Serializer):
    """Serializer for testing sensitive content patterns"""

    pattern_id = serializers.UUIDField()
    test_content = serializers.CharField(help_text="Content to test against the pattern")


class PatternTestResponseSerializer(serializers.Serializer):
    """Serializer for pattern test results"""

    pattern_name = serializers.CharField(read_only=True)
    matches_found = serializers.IntegerField(read_only=True)
    matches = serializers.ListField(read_only=True)
    execution_time_ms = serializers.FloatField(read_only=True)
