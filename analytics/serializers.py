from django.utils import timezone
from rest_framework import serializers

from .models import AnalyticsSnapshot, DataUsageMetric, PrivacyInsight, RetentionTimeline


class AnalyticsSnapshotSerializer(serializers.ModelSerializer):
    """Serializer for analytics snapshots"""

    storage_used_mb = serializers.ReadOnlyField()
    privacy_score_label = serializers.SerializerMethodField()
    security_score_label = serializers.SerializerMethodField()

    class Meta:
        model = AnalyticsSnapshot
        fields = [
            "id",
            "date",
            "total_documents",
            "total_messages",
            "total_forum_posts",
            "storage_used_bytes",
            "storage_used_mb",
            "retention_violations_count",
            "shared_documents_count",
            "public_documents_count",
            "encrypted_documents_count",
            "privacy_score",
            "privacy_score_label",
            "security_score",
            "security_score_label",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_privacy_score_label(self, obj) -> str:
        """Convert privacy score to human-readable label"""
        score = obj.privacy_score
        if score >= 90:
            return "Excellent"
        elif score >= 75:
            return "Good"
        elif score >= 60:
            return "Fair"
        elif score >= 40:
            return "Poor"
        else:
            return "Critical"

    def get_security_score_label(self, obj) -> str:
        """Convert security score to human-readable label"""
        score = obj.security_score
        if score >= 90:
            return "Secure"
        elif score >= 75:
            return "Good"
        elif score >= 60:
            return "Moderate"
        elif score >= 40:
            return "Weak"
        else:
            return "Vulnerable"


class DataUsageMetricSerializer(serializers.ModelSerializer):
    """Serializer for usage metrics"""

    formatted_value = serializers.SerializerMethodField()

    class Meta:
        model = DataUsageMetric
        fields = [
            "id",
            "metric_type",
            "metric_name",
            "value",
            "formatted_value",
            "unit",
            "timestamp",
            "metadata",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_formatted_value(self, obj) -> str:
        """Format value with appropriate unit"""
        if obj.unit == "bytes":
            # Convert bytes to human readable format
            value = float(obj.value)
            if value >= 1024**3:
                return f"{value / (1024**3):.1f} GB"
            elif value >= 1024**2:
                return f"{value / (1024**2):.1f} MB"
            elif value >= 1024:
                return f"{value / 1024:.1f} KB"
            else:
                return f"{value:.0f} B"
        elif obj.unit == "percentage":
            return f"{obj.value}%"
        else:
            return f"{obj.value} {obj.unit}"


class PrivacyInsightSerializer(serializers.ModelSerializer):
    """Serializer for privacy insights"""

    severity_color = serializers.SerializerMethodField()
    type_icon = serializers.SerializerMethodField()
    is_expired = serializers.ReadOnlyField()

    class Meta:
        model = PrivacyInsight
        fields = [
            "id",
            "insight_type",
            "type_icon",
            "severity",
            "severity_color",
            "title",
            "description",
            "action_text",
            "action_url",
            "is_read",
            "is_dismissed",
            "is_expired",
            "read_at",
            "dismissed_at",
            "context_data",
            "expires_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "read_at", "dismissed_at"]

    def get_severity_color(self, obj) -> str:
        """Get color code for severity level"""
        colors = {
            "info": "#3b82f6",  # blue
            "low": "#10b981",  # green
            "medium": "#f59e0b",  # amber
            "high": "#f97316",  # orange
            "critical": "#ef4444",  # red
        }
        return colors.get(obj.severity, "#6b7280")  # gray default

    def get_type_icon(self, obj) -> str:
        """Get icon name for insight type"""
        icons = {
            "risk": "shield-exclamation",
            "recommendation": "lightbulb",
            "alert": "exclamation-triangle",
            "tip": "information-circle",
        }
        return icons.get(obj.insight_type, "information-circle")


class RetentionTimelineSerializer(serializers.ModelSerializer):
    """Serializer for retention timeline entries"""

    days_until_deletion = serializers.SerializerMethodField()
    urgency_level = serializers.SerializerMethodField()

    class Meta:
        model = RetentionTimeline
        fields = [
            "id",
            "item_type",
            "item_id",
            "item_title",
            "scheduled_date",
            "days_until_deletion",
            "urgency_level",
            "retention_reason",
            "can_extend",
            "is_notified",
            "is_cancelled",
            "is_completed",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_days_until_deletion(self, obj) -> int:
        """Calculate days until scheduled deletion"""
        if obj.is_completed or obj.is_cancelled:
            return 0

        now = timezone.now()
        if obj.scheduled_date <= now:
            return 0

        delta = obj.scheduled_date - now
        return delta.days

    def get_urgency_level(self, obj) -> str:
        """Determine urgency level based on time remaining"""
        days = self.get_days_until_deletion(obj)

        if days <= 1:
            return "critical"
        elif days <= 7:
            return "high"
        elif days <= 30:
            return "medium"
        else:
            return "low"


class DashboardOverviewSerializer(serializers.Serializer):
    """Combined dashboard data serializer"""

    # Latest snapshot data
    current_snapshot = AnalyticsSnapshotSerializer(read_only=True)

    # Summary stats
    total_storage_mb = serializers.FloatField(read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    privacy_score = serializers.IntegerField(read_only=True)
    security_score = serializers.IntegerField(read_only=True)

    # Active insights
    critical_insights_count = serializers.IntegerField(read_only=True)
    unread_insights = PrivacyInsightSerializer(many=True, read_only=True)

    # Upcoming deletions
    pending_deletions_count = serializers.IntegerField(read_only=True)
    urgent_deletions = RetentionTimelineSerializer(many=True, read_only=True)

    # Recent trends (last 7 days)
    storage_trend = serializers.ListField(child=serializers.FloatField(), read_only=True)
    activity_trend = serializers.ListField(child=serializers.IntegerField(), read_only=True)
    privacy_score_trend = serializers.ListField(child=serializers.IntegerField(), read_only=True)


class UsageStatsSerializer(serializers.Serializer):
    """Usage statistics over time"""

    date_range = serializers.CharField(read_only=True)
    snapshots = AnalyticsSnapshotSerializer(many=True, read_only=True)
    metrics = DataUsageMetricSerializer(many=True, read_only=True)

    # Aggregated stats
    total_storage_bytes = serializers.IntegerField(read_only=True)
    avg_daily_activity = serializers.FloatField(read_only=True)
    privacy_score_change = serializers.IntegerField(read_only=True)


class PrivacyScoreBreakdownSerializer(serializers.Serializer):
    """Detailed privacy score breakdown"""

    overall_score = serializers.IntegerField(read_only=True)
    score_label = serializers.CharField(read_only=True)

    # Score components
    encryption_score = serializers.IntegerField(read_only=True)
    sharing_score = serializers.IntegerField(read_only=True)
    retention_score = serializers.IntegerField(read_only=True)
    public_data_score = serializers.IntegerField(read_only=True)

    # Recommendations
    top_recommendations = PrivacyInsightSerializer(many=True, read_only=True)

    # Historical trend
    score_history = serializers.ListField(
        child=serializers.DictField(), read_only=True, help_text="List of {date, score} objects"
    )
