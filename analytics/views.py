from datetime import date, timedelta
from typing import Any, Dict

from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import permissions
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet

from documents.models import Document
from forum.models import Post
from messaging.models import Message
from moderation.insight_generator import generate_moderation_insights
from moderation.models import ContentScan, PolicyViolation

from .models import AnalyticsSnapshot, DataUsageMetric, PrivacyInsight, RetentionTimeline
from .serializers import (
    AnalyticsSnapshotSerializer,
    DashboardOverviewSerializer,
    DataUsageMetricSerializer,
    PrivacyInsightSerializer,
    PrivacyScoreBreakdownSerializer,
    RetentionTimelineSerializer,
    UsageStatsSerializer,
)


class AnalyticsSnapshotViewSet(ReadOnlyModelViewSet):
    """ViewSet for analytics snapshots"""

    serializer_class = AnalyticsSnapshotSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Handle schema introspection
        if getattr(self, "swagger_fake_view", False):
            return AnalyticsSnapshot.objects.none()
        return AnalyticsSnapshot.objects.filter(user=self.request.user)


class DataUsageMetricViewSet(ReadOnlyModelViewSet):
    """ViewSet for usage metrics"""

    serializer_class = DataUsageMetricSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["metric_type", "metric_name"]
    ordering_fields = ["timestamp", "value"]
    ordering = ["-timestamp"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return DataUsageMetric.objects.none()
        return DataUsageMetric.objects.filter(user=self.request.user)


class PrivacyInsightViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    """ViewSet for privacy insights with action endpoints"""

    serializer_class = PrivacyInsightSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["insight_type", "severity", "is_read", "is_dismissed"]
    ordering = ["-created_at"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return PrivacyInsight.objects.none()
        return PrivacyInsight.objects.filter(user=self.request.user, is_dismissed=False).exclude(
            Q(expires_at__lt=timezone.now())
        )

    @extend_schema(summary="Mark insight as read", responses={200: PrivacyInsightSerializer})
    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        """Mark a privacy insight as read"""
        insight = self.get_object()
        insight.mark_as_read()
        serializer = self.get_serializer(insight)
        return Response(serializer.data)

    @extend_schema(summary="Dismiss insight", responses={200: PrivacyInsightSerializer})
    @action(detail=True, methods=["post"])
    def dismiss(self, request, pk=None):
        """Dismiss a privacy insight"""
        insight = self.get_object()
        insight.dismiss()
        serializer = self.get_serializer(insight)
        return Response(serializer.data)


class RetentionTimelineViewSet(ReadOnlyModelViewSet):
    """ViewSet for retention timeline entries"""

    serializer_class = RetentionTimelineSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["item_type", "can_extend", "is_cancelled"]
    ordering = ["scheduled_date"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return RetentionTimeline.objects.none()
        return RetentionTimeline.objects.filter(user=self.request.user, is_completed=False)


class AnalyticsDashboardViewSet(GenericViewSet):
    """Main dashboard API with aggregated analytics data"""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Get dashboard overview",
        responses={200: DashboardOverviewSerializer},
        description="Returns dashboard data including metrics, insights, and trends",
    )
    @action(detail=False, methods=["get"])
    def overview(self, request):
        """Get comprehensive dashboard overview"""
        user = request.user

        # Get or create today's snapshot
        today = timezone.now().date()
        current_snapshot, created = AnalyticsSnapshot.objects.get_or_create(
            user=user, date=today, defaults=self._generate_snapshot_data(user, today)
        )

        # Get recent snapshots for trends (last 7 days)
        week_ago = today - timedelta(days=7)
        recent_snapshots = AnalyticsSnapshot.objects.filter(user=user, date__gte=week_ago).order_by(
            "date"
        )

        # Get active insights
        active_insights = PrivacyInsight.objects.filter(
            user=user, is_dismissed=False, is_read=False
        ).exclude(Q(expires_at__lt=timezone.now()))

        # Get urgent deletions (next 7 days)
        next_week = timezone.now() + timedelta(days=7)
        urgent_deletions = RetentionTimeline.objects.filter(
            user=user, scheduled_date__lte=next_week, is_completed=False, is_cancelled=False
        ).order_by("scheduled_date")[:5]

        # Compile dashboard data
        data = {
            "current_snapshot": current_snapshot,
            "total_storage_mb": current_snapshot.storage_used_mb,
            "total_items": (
                current_snapshot.total_documents
                + current_snapshot.total_messages
                + current_snapshot.total_forum_posts
            ),
            "privacy_score": current_snapshot.privacy_score,
            "security_score": current_snapshot.security_score,
            "moderation_compliance_score": current_snapshot.moderation_compliance_score,
            "critical_insights_count": active_insights.filter(
                severity__in=["high", "critical"]
            ).count(),
            "unread_insights": active_insights[:5],  # Top 5 unread
            "pending_deletions_count": RetentionTimeline.objects.filter(
                user=user, is_completed=False, is_cancelled=False
            ).count(),
            "urgent_deletions": urgent_deletions,
            # Moderation metrics for dashboard
            "total_content_scans": current_snapshot.total_content_scans,
            "content_violations_found": current_snapshot.content_violations_found,
            "critical_violations_count": current_snapshot.critical_violations_count,
            "quarantined_items_count": current_snapshot.quarantined_items_count,
            "avg_content_risk_score": current_snapshot.avg_content_risk_score,
            # Trends
            "storage_trend": [s.storage_used_mb for s in recent_snapshots],
            "activity_trend": [
                (s.total_documents + s.total_messages + s.total_forum_posts)
                for s in recent_snapshots
            ],
            "privacy_score_trend": [s.privacy_score for s in recent_snapshots],
            "moderation_compliance_trend": [
                s.moderation_compliance_score for s in recent_snapshots
            ],
            "violation_trend": [s.content_violations_found for s in recent_snapshots],
        }

        serializer = DashboardOverviewSerializer(data)
        return Response(serializer.data)

    @extend_schema(summary="Get detailed usage statistics", responses={200: UsageStatsSerializer})
    @action(detail=False, methods=["get"])
    def usage_stats(self, request):
        """Get detailed usage statistics over time"""
        user = request.user
        days = int(request.query_params.get("days", 30))

        start_date = timezone.now().date() - timedelta(days=days)

        # Get snapshots for the period
        snapshots = AnalyticsSnapshot.objects.filter(user=user, date__gte=start_date).order_by(
            "date"
        )

        # Get metrics for the period
        metrics = DataUsageMetric.objects.filter(user=user, timestamp__gte=start_date).order_by(
            "timestamp"
        )

        # Calculate aggregates
        total_storage = (
            snapshots.aggregate(Sum("storage_used_bytes"))["storage_used_bytes__sum"] or 0
        )
        avg_activity = (
            snapshots.aggregate(
                avg_activity=Avg("total_documents")
                + Avg("total_messages")
                + Avg("total_forum_posts")
            )["avg_activity"]
            or 0
        )

        # Privacy score change
        first_snapshot = snapshots.first()
        last_snapshot = snapshots.last()
        privacy_score_change = 0
        if first_snapshot and last_snapshot:
            privacy_score_change = last_snapshot.privacy_score - first_snapshot.privacy_score

        data = {
            "date_range": f"{start_date} to {timezone.now().date()}",
            "snapshots": snapshots,
            "metrics": metrics,
            "total_storage_bytes": total_storage,
            "avg_daily_activity": round(avg_activity, 1),
            "privacy_score_change": privacy_score_change,
        }

        serializer = UsageStatsSerializer(data)
        return Response(serializer.data)

    @extend_schema(
        summary="Get privacy score breakdown", responses={200: PrivacyScoreBreakdownSerializer}
    )
    @action(detail=False, methods=["get"])
    def privacy_score(self, request):
        """Get detailed privacy score breakdown and recommendations"""
        user = request.user

        # Get latest snapshot
        latest_snapshot = AnalyticsSnapshot.objects.filter(user=user).first()
        if not latest_snapshot:
            # Generate one if none exists
            today = timezone.now().date()
            latest_snapshot = AnalyticsSnapshot.objects.create(
                user=user, date=today, **self._generate_snapshot_data(user, today)
            )

        # Calculate component scores
        component_scores = self._calculate_component_scores(latest_snapshot)

        # Get score history (last 30 days)
        month_ago = timezone.now().date() - timedelta(days=30)
        score_history = list(
            AnalyticsSnapshot.objects.filter(user=user, date__gte=month_ago)
            .values("date", "privacy_score")
            .order_by("date")
        )

        # Get top recommendations
        recommendations = PrivacyInsight.objects.filter(
            user=user, insight_type="recommendation", is_dismissed=False
        ).exclude(Q(expires_at__lt=timezone.now()))[:3]

        # Score label
        score = latest_snapshot.privacy_score
        if score >= 90:
            label = "Excellent"
        elif score >= 75:
            label = "Good"
        elif score >= 60:
            label = "Fair"
        elif score >= 40:
            label = "Poor"
        else:
            label = "Critical"

        data = {
            "overall_score": latest_snapshot.privacy_score,
            "score_label": label,
            "encryption_score": component_scores["encryption"],
            "sharing_score": component_scores["sharing"],
            "retention_score": component_scores["retention"],
            "public_data_score": component_scores["public_data"],
            "top_recommendations": recommendations,
            "score_history": score_history,
        }

        serializer = PrivacyScoreBreakdownSerializer(data)
        return Response(serializer.data)

    def _generate_snapshot_data(self, user, date: date) -> Dict[str, Any]:
        """Generate analytics snapshot data for a user on a given date"""

        # Count documents
        documents = Document.objects.filter(owner=user)
        doc_stats = documents.aggregate(
            total=Count("id"),
            shared=Count("id", filter=Q(shared_with__isnull=False)),
            public=Count("id", filter=Q(is_public=True)),
            encrypted=Count("id", filter=Q(is_encrypted=True)),
            storage=Sum("file_size"),
        )

        # Count messages
        messages_count = Message.objects.filter(sender=user).count()

        # Count forum posts
        posts_count = Post.objects.filter(author=user).count()

        # Count retention violations (items past their intended deletion date)
        retention_violations = 0
        retention_violations += Document.objects.filter(
            owner=user, retention_date__lt=timezone.now()
        ).count()
        retention_violations += Message.objects.filter(
            sender=user, retention_date__lt=timezone.now()
        ).count()
        retention_violations += Post.objects.filter(
            author=user, retention_date__lt=timezone.now()
        ).count()

        # Count moderation violations and scan data (ENHANCED)
        moderation_scans = ContentScan.objects.filter(user=user, scan_status="completed")
        total_scans = moderation_scans.count()

        # Get all violations for this user
        all_violations = PolicyViolation.objects.filter(content_scan__user=user)
        total_violations = all_violations.count()
        critical_violations = all_violations.filter(severity="critical", is_resolved=False).count()
        recent_violations = all_violations.filter(
            created_at__gte=timezone.now() - timedelta(days=7)
        ).count()

        # Calculate average risk score from scans
        avg_risk_score = 0.0
        if total_scans > 0:
            risk_scores = moderation_scans.values_list("scan_score", flat=True)
            avg_risk_score = sum(risk_scores) / len(risk_scores) if risk_scores else 0.0

        # Count quarantined items (moderation actions with quarantine)
        from moderation.models import ActionType, ModerationAction

        quarantined_count = ModerationAction.objects.filter(
            content_scan__user=user,
            action_type=ActionType.QUARANTINE,
            expiry_date__gt=timezone.now(),  # Still active
        ).count()

        # Generate privacy insights based on recent violations
        insights_generated = 0
        if recent_violations > 0:
            try:
                insights_generated = generate_moderation_insights(user)
            except Exception as e:
                # Log the error but don't fail the snapshot creation
                print(f"Warning: Failed to generate insights for {user.username}: {e}")

        snapshot_data = {
            "total_documents": doc_stats["total"] or 0,
            "total_messages": messages_count,
            "total_forum_posts": posts_count,
            "storage_used_bytes": doc_stats["storage"] or 0,
            "retention_violations_count": retention_violations,
            "shared_documents_count": doc_stats["shared"] or 0,
            "public_documents_count": doc_stats["public"] or 0,
            "encrypted_documents_count": doc_stats["encrypted"] or 0,
            # New moderation metrics
            "total_content_scans": total_scans,
            "content_violations_found": total_violations,
            "critical_violations_count": critical_violations,
            "avg_content_risk_score": avg_risk_score,
            "quarantined_items_count": quarantined_count,
        }

        # Calculate privacy score
        snapshot = AnalyticsSnapshot(**snapshot_data)
        snapshot_data["privacy_score"] = snapshot.calculate_privacy_score()

        # Calculate security score (simplified for now)
        snapshot_data["security_score"] = self._calculate_security_score(user, snapshot_data)

        # Calculate moderation compliance score
        snapshot = AnalyticsSnapshot(**snapshot_data)
        snapshot_data["moderation_compliance_score"] = (
            snapshot.calculate_moderation_compliance_score()
        )

        return snapshot_data

    def _calculate_security_score(self, user, snapshot_data: Dict[str, Any]) -> int:
        """Calculate security score based on user's security settings"""
        score = 100

        # Check if user has 2FA enabled
        if hasattr(user, "profile") and not user.profile.enable_two_factor:
            score -= 25

        # Check encryption usage
        total_docs = snapshot_data["total_documents"]
        if total_docs > 0:
            encryption_ratio = snapshot_data["encrypted_documents_count"] / total_docs
            score -= int((1 - encryption_ratio) * 30)

        # Check for public documents
        if snapshot_data["public_documents_count"] > 0:
            score -= min(snapshot_data["public_documents_count"] * 5, 20)

        return max(0, min(100, score))

    def _calculate_component_scores(self, snapshot: AnalyticsSnapshot) -> Dict[str, int]:
        """Calculate individual component scores for privacy breakdown"""

        scores = {}

        # Encryption score
        if snapshot.total_documents > 0:
            encryption_ratio = snapshot.encrypted_documents_count / snapshot.total_documents
            scores["encryption"] = int(encryption_ratio * 100)
        else:
            scores["encryption"] = 100

        # Sharing score (lower is better for privacy)
        if snapshot.total_documents > 0:
            sharing_ratio = snapshot.shared_documents_count / snapshot.total_documents
            scores["sharing"] = int((1 - sharing_ratio) * 100)
        else:
            scores["sharing"] = 100

        # Retention score
        if snapshot.retention_violations_count > 0:
            scores["retention"] = max(0, 100 - (snapshot.retention_violations_count * 10))
        else:
            scores["retention"] = 100

        # Public data score
        if snapshot.total_documents > 0:
            public_ratio = snapshot.public_documents_count / snapshot.total_documents
            scores["public_data"] = int((1 - public_ratio) * 100)
        else:
            scores["public_data"] = 100

        return scores
