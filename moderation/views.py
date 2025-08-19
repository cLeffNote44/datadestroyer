"""
Django REST Framework API views for content moderation system.

Provides comprehensive APIs for:
- Content scanning and analysis
- Policy violation management
- Moderation actions and workflows
- Pattern management and testing
- Dashboard and analytics integration
"""

import time
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from .admin_workflows import admin_review_queue, get_admin_dashboard_data
from .content_analyzer import moderation_engine
from .models import (
    ActionType,
    ContentScan,
    ModerationAction,
    ModerationSettings,
    ModerationStatus,
    PolicyViolation,
    SensitiveContentPattern,
    SensitivityLevel,
)
from .serializers import (
    BulkScanRequestSerializer,
    ContentScanRequestSerializer,
    ContentScanResponseSerializer,
    ContentScanSerializer,
    ModerationActionSerializer,
    ModerationDashboardSerializer,
    ModerationSettingsSerializer,
    PatternTestResponseSerializer,
    PatternTestSerializer,
    PolicyViolationSerializer,
    QuarantineActionSerializer,
    SensitiveContentPatternSerializer,
    ViolationResolutionSerializer,
)

User = get_user_model()


class SensitiveContentPatternViewSet(ModelViewSet):
    """
    API endpoints for managing sensitive content patterns.

    Provides CRUD operations for pattern management including:
    - List/create/update/delete patterns
    - Test patterns against sample content
    - Enable/disable patterns
    - Pattern performance analytics
    """

    serializer_class = SensitiveContentPatternSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter patterns based on user permissions"""
        user = self.request.user
        if user.is_staff:
            return SensitiveContentPattern.objects.all()
        else:
            # Regular users can only see active patterns
            return SensitiveContentPattern.objects.filter(is_active=True)

    @action(detail=True, methods=["post"])
    def test_pattern(self, request, pk=None):
        """Test a pattern against sample content"""
        pattern = self.get_object()
        serializer = PatternTestSerializer(data=request.data)

        if serializer.is_valid():
            test_content = serializer.validated_data["test_content"]
            start_time = time.time()

            try:
                matches = pattern.test_content(test_content)
                execution_time_ms = (time.time() - start_time) * 1000

                response_data = {
                    "pattern_name": pattern.name,
                    "matches_found": len(matches),
                    "matches": matches,
                    "execution_time_ms": execution_time_ms,
                }

                response_serializer = PatternTestResponseSerializer(response_data)
                return Response(response_serializer.data)

            except Exception as e:
                return Response(
                    {"error": f"Pattern test failed: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def toggle_active(self, request, pk=None):
        """Toggle pattern active status"""
        if not request.user.is_staff:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        pattern = self.get_object()
        pattern.is_active = not pattern.is_active
        pattern.save()

        # Refresh analyzer patterns
        ContentAnalyzer().refresh_patterns()

        serializer = self.get_serializer(pattern)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def statistics(self, request):
        """Get pattern usage statistics"""
        if not request.user.is_staff:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        stats = {}
        patterns = self.get_queryset()

        for pattern in patterns:
            violation_count = PolicyViolation.objects.filter(pattern=pattern).count()
            recent_violations = PolicyViolation.objects.filter(
                pattern=pattern, created_at__gte=timezone.now() - timedelta(days=30)
            ).count()

            stats[str(pattern.id)] = {
                "name": pattern.name,
                "total_violations": violation_count,
                "recent_violations": recent_violations,
                "is_active": pattern.is_active,
            }

        return Response(stats)


class ContentScanViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    """
    API endpoints for viewing content scan results.

    Provides read-only access to scan history and results.
    """

    serializer_class = ContentScanSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return scans for current user"""
        return (
            ContentScan.objects.filter(user=self.request.user)
            .prefetch_related("violations__pattern")
            .order_by("-scanned_at")
        )

    @action(detail=False, methods=["get"])
    def recent(self, request):
        """Get recent scans for dashboard"""
        recent_scans = self.get_queryset()[:10]
        serializer = self.get_serializer(recent_scans, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def high_risk(self, request):
        """Get high-risk content scans"""
        high_risk_scans = self.get_queryset().filter(scan_score__gte=60)
        serializer = self.get_serializer(high_risk_scans, many=True)
        return Response(serializer.data)


class PolicyViolationViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    """
    API endpoints for managing policy violations.

    Provides access to violation details and resolution functionality.
    """

    serializer_class = PolicyViolationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return violations for current user"""
        return (
            PolicyViolation.objects.filter(content_scan__user=self.request.user)
            .select_related("pattern", "content_scan", "resolved_by")
            .order_by("-created_at")
        )

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        """Resolve a policy violation"""
        violation = self.get_object()
        serializer = ViolationResolutionSerializer(data=request.data)

        if serializer.is_valid():
            action = serializer.validated_data["action"]
            notes = serializer.validated_data.get("notes", "")

            violation.resolve(action, request.user, notes)

            response_serializer = self.get_serializer(violation)
            return Response(response_serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"])
    def unresolved(self, request):
        """Get unresolved violations"""
        unresolved = self.get_queryset().filter(is_resolved=False)
        serializer = self.get_serializer(unresolved, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def by_type(self, request):
        """Get violations grouped by type"""
        violation_types = (
            self.get_queryset()
            .values("violation_type")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        return Response(list(violation_types))


class ModerationActionViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    """
    API endpoints for viewing moderation actions.
    """

    serializer_class = ModerationActionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return actions for current user"""
        return (
            ModerationAction.objects.filter(triggered_by=self.request.user)
            .select_related("content_scan", "violation", "reviewed_by")
            .order_by("-created_at")
        )

    @action(detail=True, methods=["post"])
    def acknowledge(self, request, pk=None):
        """Acknowledge a moderation action"""
        action = self.get_object()
        action.user_acknowledged = True
        action.save()

        serializer = self.get_serializer(action)
        return Response(serializer.data)


class ContentScanAPIView(APIView):
    """
    API endpoint for scanning content for sensitive information.

    POST /api/moderation/scan/
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Scan content and return results"""
        serializer = ContentScanRequestSerializer(data=request.data)

        if serializer.is_valid():
            content = serializer.validated_data["content"]
            content_type_name = serializer.validated_data.get("content_type")
            object_id = serializer.validated_data.get("object_id")
            scan_type = serializer.validated_data["scan_type"]

            try:
                # Create a mock content object for analysis
                if content_type_name and object_id:
                    # Try to find actual content object
                    try:
                        content_type = ContentType.objects.get(model=content_type_name)
                        content_object = content_type.get_object_for_this_type(pk=object_id)
                    except (ContentType.DoesNotExist, content_type.model_class().DoesNotExist):
                        content_object = None
                else:
                    content_object = None

                # Use moderation engine to process content
                if content_object:
                    result = moderation_engine.process_content(
                        content_object, request.user, content
                    )
                else:
                    # Create temporary scan for standalone content
                    analyzer = ContentAnalyzer()
                    scan_result = analyzer.analyze_content(content)

                    result = {
                        "status": "completed",
                        "scan_id": None,
                        "violations_found": scan_result.violations_found,
                        "scan_score": scan_result.scan_score,
                        "risk_level": (
                            "High"
                            if scan_result.scan_score >= 60
                            else "Medium"
                            if scan_result.scan_score >= 40
                            else "Low"
                        ),
                        "processing_time_ms": scan_result.processing_time_ms,
                        "recommended_actions": [],
                        "violations": [],
                    }

                response_serializer = ContentScanResponseSerializer(result)
                return Response(response_serializer.data)

            except Exception as e:
                return Response(
                    {"error": f"Scanning failed: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BulkScanAPIView(APIView):
    """
    API endpoint for bulk content scanning.

    POST /api/moderation/bulk-scan/
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Perform bulk scanning of multiple content items"""
        serializer = BulkScanRequestSerializer(data=request.data)

        if serializer.is_valid():
            content_items = serializer.validated_data["content_items"]
            scan_type = serializer.validated_data["scan_type"]

            results = []
            analyzer = ContentAnalyzer()

            for i, item in enumerate(content_items):
                try:
                    content = item["content"]
                    scan_result = analyzer.analyze_content(content)

                    results.append(
                        {
                            "index": i,
                            "status": "completed",
                            "violations_found": scan_result.violations_found,
                            "scan_score": scan_result.scan_score,
                            "risk_level": scan_result.violations_found > 0,
                            "processing_time_ms": scan_result.processing_time_ms,
                        }
                    )

                except Exception as e:
                    results.append({"index": i, "status": "failed", "error": str(e)})

            return Response(
                {
                    "total_items": len(content_items),
                    "completed": len([r for r in results if r["status"] == "completed"]),
                    "failed": len([r for r in results if r["status"] == "failed"]),
                    "results": results,
                }
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class QuarantineAPIView(APIView):
    """
    API endpoint for quarantine actions.

    POST /api/moderation/quarantine/
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Quarantine content based on scan results"""
        serializer = QuarantineActionSerializer(data=request.data)

        if serializer.is_valid():
            scan_ids = serializer.validated_data["scan_ids"]
            reason = serializer.validated_data["reason"]
            expiry_days = serializer.validated_data["expiry_days"]

            quarantined_scans = []

            for scan_id in scan_ids:
                try:
                    content_scan = ContentScan.objects.get(id=scan_id, user=request.user)

                    # Create quarantine action
                    action = ModerationAction.objects.create(
                        content_scan=content_scan,
                        action_type=ActionType.QUARANTINE,
                        action_status=ModerationStatus.APPROVED,
                        reason=reason,
                        automated=False,
                        triggered_by=request.user,
                        expiry_date=timezone.now() + timedelta(days=expiry_days),
                    )

                    quarantined_scans.append(str(content_scan.id))

                except ContentScan.DoesNotExist:
                    continue

            return Response(
                {
                    "quarantined_scans": quarantined_scans,
                    "total_quarantined": len(quarantined_scans),
                    "expiry_date": (timezone.now() + timedelta(days=expiry_days)).isoformat(),
                }
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ModerationDashboardAPIView(APIView):
    """
    API endpoint for moderation dashboard data.

    GET /api/moderation/dashboard/
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get comprehensive dashboard data"""
        user = request.user
        now = timezone.now()
        last_30_days = now - timedelta(days=30)

        # Basic counts
        total_scans = ContentScan.objects.filter(user=user).count()
        recent_violations = PolicyViolation.objects.filter(
            content_scan__user=user, created_at__gte=last_30_days
        ).count()

        high_risk_content = ContentScan.objects.filter(user=user, scan_score__gte=60).count()

        quarantined_items = ModerationAction.objects.filter(
            triggered_by=user,
            action_type=ActionType.QUARANTINE,
            action_status__in=[ModerationStatus.APPROVED, ModerationStatus.PENDING],
        ).count()

        pending_reviews = PolicyViolation.objects.filter(
            content_scan__user=user, is_resolved=False
        ).count()

        # Trends data (last 30 days by day)
        violation_trends = []
        for i in range(30):
            day = last_30_days + timedelta(days=i)
            day_count = PolicyViolation.objects.filter(
                content_scan__user=user, created_at__date=day.date()
            ).count()
            violation_trends.append({"date": day.date().isoformat(), "violations": day_count})

        # Risk distribution
        risk_distribution = {
            "low": ContentScan.objects.filter(user=user, scan_score__lt=40).count(),
            "medium": ContentScan.objects.filter(user=user, scan_score__range=(40, 59)).count(),
            "high": ContentScan.objects.filter(user=user, scan_score__range=(60, 79)).count(),
            "critical": ContentScan.objects.filter(user=user, scan_score__gte=80).count(),
        }

        # Top violation types
        top_violation_types = list(
            PolicyViolation.objects.filter(content_scan__user=user)
            .values("violation_type")
            .annotate(count=Count("id"))
            .order_by("-count")[:5]
        )

        # Recent scans and critical violations
        recent_scans = ContentScan.objects.filter(user=user).order_by("-scanned_at")[:5]
        critical_violations = PolicyViolation.objects.filter(
            content_scan__user=user, severity=SensitivityLevel.CRITICAL, is_resolved=False
        )[:5]

        dashboard_data = {
            "total_scans": total_scans,
            "recent_violations": recent_violations,
            "high_risk_content": high_risk_content,
            "quarantined_items": quarantined_items,
            "pending_reviews": pending_reviews,
            "violation_trends": violation_trends,
            "risk_distribution": risk_distribution,
            "top_violation_types": top_violation_types,
            "recent_scans": ContentScanSerializer(recent_scans, many=True).data,
            "critical_violations": PolicyViolationSerializer(critical_violations, many=True).data,
        }

        serializer = ModerationDashboardSerializer(dashboard_data)
        return Response(serializer.data)


class ModerationSettingsViewSet(ModelViewSet):
    """
    API endpoints for user moderation settings.
    """

    serializer_class = ModerationSettingsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return settings for current user only"""
        return ModerationSettings.objects.filter(user=self.request.user)

    def get_object(self):
        """Get or create user's moderation settings"""
        settings, created = ModerationSettings.objects.get_or_create(user=self.request.user)
        return settings

    @action(detail=False, methods=["get"])
    def my_settings(self, request):
        """Get current user's moderation settings"""
        settings = self.get_object()
        serializer = self.get_serializer(settings)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def update_settings(self, request):
        """Update current user's moderation settings"""
        settings = self.get_object()
        serializer = self.get_serializer(settings, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminReviewQueueAPIView(APIView):
    """
    Admin API endpoint for review queue management.

    GET /api/moderation/admin/review-queue/
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get pending review items for admin"""
        if not request.user.is_staff:
            return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)

        priority_filter = request.query_params.get("priority", "all")
        review_items = admin_review_queue.get_pending_reviews(priority_filter)

        return Response(
            {
                "items": review_items,
                "total_pending": len(review_items),
                "statistics": admin_review_queue.get_review_statistics(),
            }
        )


class AdminReviewActionAPIView(APIView):
    """
    Admin API endpoint for review actions.

    POST /api/moderation/admin/review-action/
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Perform admin review action"""
        if not request.user.is_staff:
            return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)

        action_id = request.data.get("action_id")
        decision = request.data.get("decision")  # 'approve', 'require_user_action', 'escalate'
        notes = request.data.get("notes", "")

        if not action_id or not decision:
            return Response(
                {"error": "action_id and decision are required"}, status=status.HTTP_400_BAD_REQUEST
            )

        if decision == "approve":
            result = admin_review_queue.approve_content(action_id, request.user, notes)
        elif decision == "require_user_action":
            required_action = request.data.get("required_action", "review")
            result = admin_review_queue.require_user_action(
                action_id, request.user, required_action, notes
            )
        elif decision == "escalate":
            result = admin_review_queue.escalate_to_security_team(action_id, request.user, notes)
        else:
            return Response({"error": "Invalid decision type"}, status=status.HTTP_400_BAD_REQUEST)

        return Response(result)


class AdminBulkReviewAPIView(APIView):
    """
    Admin API endpoint for bulk review actions.

    POST /api/moderation/admin/bulk-review/
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Perform bulk admin review actions"""
        if not request.user.is_staff:
            return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)

        action_ids = request.data.get("action_ids", [])
        decision = request.data.get("decision")
        notes = request.data.get("notes", "")

        if not action_ids or not decision:
            return Response(
                {"error": "action_ids and decision are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if decision == "approve":
            result = admin_review_queue.bulk_approve(action_ids, request.user, notes)
        else:
            return Response(
                {"error": "Only bulk approve is currently supported"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(result)


class AdminDashboardAPIView(APIView):
    """
    Admin API endpoint for moderation dashboard data.

    GET /api/moderation/admin/dashboard/
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get admin dashboard data"""
        if not request.user.is_staff:
            return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)

        dashboard_data = get_admin_dashboard_data()
        return Response(dashboard_data)
