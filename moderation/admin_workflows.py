"""
Admin workflow system for moderation review and actions

Provides tools for administrators to review flagged content,
manage quarantine actions, and handle bulk moderation tasks.
"""

import logging
from datetime import timedelta
from typing import Any, Dict, List

from django.contrib.auth import get_user_model
from django.db.models import Count
from django.utils import timezone

from .models import (
    ActionType,
    ContentScan,
    ModerationAction,
    ModerationStatus,
    PolicyViolation,
    SensitivityLevel,
)
from .notifications import send_review_required_notification

User = get_user_model()
logger = logging.getLogger("moderation.admin_workflows")


class AdminReviewQueue:
    """Manages the admin review queue for flagged content"""

    def get_pending_reviews(self, priority_filter: str = "all") -> List[Dict[str, Any]]:
        """
        Get list of content requiring admin review

        Args:
            priority_filter: 'all', 'critical', 'high', 'medium', 'low'

        Returns:
            List of review items with metadata
        """
        # Get all pending review actions
        base_query = (
            ModerationAction.objects.filter(
                action_type=ActionType.REQUIRE_REVIEW, action_status=ModerationStatus.PENDING
            )
            .select_related("content_scan", "content_scan__user", "violation")
            .order_by("-created_at")
        )

        # Apply priority filter
        if priority_filter != "all":
            # Filter by violation severity
            severity_map = {
                "critical": SensitivityLevel.CRITICAL,
                "high": SensitivityLevel.HIGH,
                "medium": SensitivityLevel.MEDIUM,
                "low": SensitivityLevel.LOW,
            }
            if priority_filter in severity_map:
                base_query = base_query.filter(violation__severity=severity_map[priority_filter])

        review_items = []
        for action in base_query[:50]:  # Limit to 50 items for performance
            # Get violation summary
            violation_summary = self._get_violation_summary(action.content_scan)

            # Calculate days pending
            days_pending = (timezone.now() - action.created_at).days

            review_item = {
                "action_id": str(action.id),
                "content_scan_id": str(action.content_scan.id),
                "user": {
                    "username": action.content_scan.user.username,
                    "email": action.content_scan.user.email,
                    "id": action.content_scan.user.id,
                },
                "risk_level": action.action_data.get("risk_level", "Unknown"),
                "violations_count": action.action_data.get("violations_count", 0),
                "highest_severity": violation_summary["highest_severity"],
                "violation_types": violation_summary["types"],
                "content_type": action.content_scan.content_type.model,
                "content_length": action.content_scan.content_length,
                "scan_score": action.content_scan.scan_score,
                "created_at": action.created_at,
                "days_pending": days_pending,
                "reason": action.reason,
                "auto_flagged": action.action_data.get("auto_flagged", False),
                "priority_score": self._calculate_priority_score(action, violation_summary),
            }
            review_items.append(review_item)

        # Sort by priority score (highest first)
        review_items.sort(key=lambda x: x["priority_score"], reverse=True)

        return review_items

    def get_review_statistics(self) -> Dict[str, Any]:
        """Get statistics about the review queue"""
        pending_reviews = ModerationAction.objects.filter(
            action_type=ActionType.REQUIRE_REVIEW, action_status=ModerationStatus.PENDING
        )

        # Count by severity
        severity_counts = {}
        for severity in [
            SensitivityLevel.CRITICAL,
            SensitivityLevel.HIGH,
            SensitivityLevel.MEDIUM,
            SensitivityLevel.LOW,
        ]:
            count = pending_reviews.filter(violation__severity=severity).count()
            severity_counts[severity] = count

        # Age distribution
        now = timezone.now()
        age_distribution = {
            "today": pending_reviews.filter(created_at__gte=now - timedelta(days=1)).count(),
            "this_week": pending_reviews.filter(created_at__gte=now - timedelta(days=7)).count(),
            "this_month": pending_reviews.filter(created_at__gte=now - timedelta(days=30)).count(),
            "older": pending_reviews.filter(created_at__lt=now - timedelta(days=30)).count(),
        }

        # User distribution (top 10 users with most pending reviews)
        user_distribution = list(
            pending_reviews.values("content_scan__user__username")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        return {
            "total_pending": pending_reviews.count(),
            "severity_counts": severity_counts,
            "age_distribution": age_distribution,
            "user_distribution": user_distribution,
            "avg_pending_days": self._calculate_avg_pending_days(pending_reviews),
        }

    def approve_content(self, action_id: str, admin_user, notes: str = "") -> Dict[str, Any]:
        """
        Approve flagged content (remove from quarantine, allow sharing)

        Args:
            action_id: ModerationAction ID
            admin_user: Admin user performing the action
            notes: Optional notes about the decision

        Returns:
            Result dictionary
        """
        try:
            action = ModerationAction.objects.get(id=action_id)

            # Update the review action
            action.action_status = ModerationStatus.APPROVED
            action.reviewed_by = admin_user
            action.action_data.update(
                {
                    "admin_decision": "approved",
                    "admin_notes": notes,
                    "reviewed_at": timezone.now().isoformat(),
                }
            )
            action.save()

            # Create approval action
            approval_action = ModerationAction.objects.create(
                content_scan=action.content_scan,
                action_type=ActionType.APPROVE,
                action_status=ModerationStatus.APPROVED,
                reason=(
                    f"Admin approved after review: {notes}"
                    if notes
                    else "Admin approved after review"
                ),
                automated=False,
                triggered_by=admin_user,
                reviewed_by=admin_user,
                action_data={
                    "approved_by": admin_user.username,
                    "approval_notes": notes,
                    "original_action_id": str(action.id),
                },
            )

            # Remove any active quarantine or sharing blocks
            self._remove_restrictions(action.content_scan, admin_user)

            logger.info(
                f"Admin {admin_user.username} approved content scan {action.content_scan.id}"
            )

            return {
                "success": True,
                "action_id": str(approval_action.id),
                "message": "Content approved and restrictions removed",
            }

        except ModerationAction.DoesNotExist:
            return {"success": False, "error": "Review action not found"}
        except Exception as e:
            logger.error(f"Error approving content: {str(e)}")
            return {"success": False, "error": str(e)}

    def require_user_action(
        self, action_id: str, admin_user, required_action: str, notes: str = ""
    ) -> Dict[str, Any]:
        """
        Require user to take action on flagged content

        Args:
            action_id: ModerationAction ID
            admin_user: Admin user performing the action
            required_action: Type of action required ('modify', 'remove', 'encrypt', 'restrict_sharing')
            notes: Notes explaining what the user needs to do

        Returns:
            Result dictionary
        """
        try:
            action = ModerationAction.objects.get(id=action_id)

            # Update the review action
            action.action_status = ModerationStatus.REQUIRES_REVIEW  # Still needs attention
            action.reviewed_by = admin_user
            action.action_data.update(
                {
                    "admin_decision": "requires_user_action",
                    "required_action": required_action,
                    "admin_notes": notes,
                    "reviewed_at": timezone.now().isoformat(),
                }
            )
            action.save()

            # Create a new action requiring user response
            user_action = ModerationAction.objects.create(
                content_scan=action.content_scan,
                action_type=ActionType.REQUIRE_REVIEW,
                action_status=ModerationStatus.PENDING,
                reason=f"Admin requires user action: {required_action}",
                automated=False,
                triggered_by=admin_user,
                action_data={
                    "admin_required": True,
                    "required_action": required_action,
                    "admin_notes": notes,
                    "original_action_id": str(action.id),
                    "user_notified": False,
                },
            )

            # Send notification to user
            try:
                send_review_required_notification(action.content_scan.user, user_action)
                user_action.action_data["user_notified"] = True
                user_action.save()
            except Exception as e:
                logger.error(f"Failed to send user notification: {str(e)}")

            logger.info(
                f"Admin {admin_user.username} required user action for scan {action.content_scan.id}"
            )

            return {
                "success": True,
                "action_id": str(user_action.id),
                "message": f"User notified to {required_action}",
            }

        except ModerationAction.DoesNotExist:
            return {"success": False, "error": "Review action not found"}
        except Exception as e:
            logger.error(f"Error requiring user action: {str(e)}")
            return {"success": False, "error": str(e)}

    def escalate_to_security_team(
        self, action_id: str, admin_user, notes: str = ""
    ) -> Dict[str, Any]:
        """
        Escalate content to security team for further review

        Args:
            action_id: ModerationAction ID
            admin_user: Admin user performing escalation
            notes: Notes about why escalation is needed

        Returns:
            Result dictionary
        """
        try:
            action = ModerationAction.objects.get(id=action_id)

            # Update the review action
            action.action_status = ModerationStatus.REQUIRES_REVIEW
            action.reviewed_by = admin_user
            action.action_data.update(
                {
                    "admin_decision": "escalated",
                    "escalation_reason": notes,
                    "escalated_by": admin_user.username,
                    "escalated_at": timezone.now().isoformat(),
                }
            )
            action.save()

            # Create escalation action
            escalation_action = ModerationAction.objects.create(
                content_scan=action.content_scan,
                action_type=ActionType.REQUIRE_REVIEW,
                action_status=ModerationStatus.PENDING,
                reason=(
                    f"Escalated to security team: {notes}"
                    if notes
                    else "Escalated to security team"
                ),
                automated=False,
                triggered_by=admin_user,
                action_data={
                    "escalated": True,
                    "escalation_level": "security_team",
                    "escalated_by": admin_user.username,
                    "escalation_reason": notes,
                    "original_action_id": str(action.id),
                    "requires_security_review": True,
                },
            )

            # TODO: Send notification to security team
            # This would typically send an email or create a ticket

            logger.info(
                f"Admin {admin_user.username} escalated scan {action.content_scan.id} to security team"
            )

            return {
                "success": True,
                "action_id": str(escalation_action.id),
                "message": "Content escalated to security team",
            }

        except ModerationAction.DoesNotExist:
            return {"success": False, "error": "Review action not found"}
        except Exception as e:
            logger.error(f"Error escalating content: {str(e)}")
            return {"success": False, "error": str(e)}

    def bulk_approve(self, action_ids: List[str], admin_user, notes: str = "") -> Dict[str, Any]:
        """
        Bulk approve multiple review actions

        Args:
            action_ids: List of ModerationAction IDs
            admin_user: Admin user performing bulk action
            notes: Notes for the bulk action

        Returns:
            Result dictionary with success/failure counts
        """
        successful = 0
        failed = 0
        errors = []

        for action_id in action_ids:
            result = self.approve_content(action_id, admin_user, notes)
            if result["success"]:
                successful += 1
            else:
                failed += 1
                errors.append(f"Action {action_id}: {result.get('error', 'Unknown error')}")

        logger.info(
            f"Admin {admin_user.username} bulk approved {successful} items, {failed} failed"
        )

        return {
            "success": True,
            "successful_count": successful,
            "failed_count": failed,
            "errors": errors,
            "message": f"Bulk operation completed: {successful} approved, {failed} failed",
        }

    def _get_violation_summary(self, content_scan: ContentScan) -> Dict[str, Any]:
        """Get summary of violations for a content scan"""
        violations = PolicyViolation.objects.filter(content_scan=content_scan)

        if not violations.exists():
            return {"count": 0, "highest_severity": "none", "types": []}

        # Get highest severity
        severity_order = ["critical", "high", "medium", "low"]
        highest_severity = "low"
        for severity in severity_order:
            if violations.filter(severity=severity).exists():
                highest_severity = severity
                break

        # Get unique violation types
        violation_types = list(violations.values_list("violation_type", flat=True).distinct())

        return {
            "count": violations.count(),
            "highest_severity": highest_severity,
            "types": violation_types,
        }

    def _calculate_priority_score(self, action: ModerationAction, violation_summary: Dict) -> int:
        """Calculate priority score for review queue ordering"""
        score = 0

        # Severity score
        severity_scores = {"critical": 100, "high": 75, "medium": 50, "low": 25}
        score += severity_scores.get(violation_summary["highest_severity"], 0)

        # Age score (older = higher priority)
        days_pending = (timezone.now() - action.created_at).days
        score += min(days_pending * 5, 50)  # Max 50 points for age

        # Risk level score
        risk_levels = {"Critical": 50, "High": 35, "Medium": 20, "Low": 10}
        risk_level = action.action_data.get("risk_level", "Unknown")
        score += risk_levels.get(risk_level, 0)

        # Multiple violations boost
        violations_count = violation_summary["count"]
        if violations_count > 1:
            score += min(violations_count * 10, 30)

        return score

    def _calculate_avg_pending_days(self, queryset) -> float:
        """Calculate average days pending for a queryset"""
        if not queryset.exists():
            return 0.0

        now = timezone.now()
        total_days = sum((now - action.created_at).days for action in queryset)
        return round(total_days / queryset.count(), 1)

    def _remove_restrictions(self, content_scan: ContentScan, admin_user):
        """Remove quarantine and sharing restrictions for approved content"""

        # Find active quarantine actions
        quarantine_actions = ModerationAction.objects.filter(
            content_scan=content_scan,
            action_type=ActionType.QUARANTINE,
            action_status__in=[ModerationStatus.PENDING, ModerationStatus.APPROVED],
            expiry_date__gt=timezone.now(),
        )

        # Release from quarantine
        for quarantine in quarantine_actions:
            quarantine.action_status = ModerationStatus.APPROVED
            quarantine.reviewed_by = admin_user
            quarantine.action_data.update(
                {
                    "released_early": True,
                    "released_by": admin_user.username,
                    "released_at": timezone.now().isoformat(),
                }
            )
            quarantine.save()

            # Create release action
            ModerationAction.objects.create(
                content_scan=content_scan,
                action_type=ActionType.RELEASE,
                action_status=ModerationStatus.APPROVED,
                reason="Released from quarantine by admin approval",
                automated=False,
                triggered_by=admin_user,
                action_data={
                    "released_by": admin_user.username,
                    "original_quarantine_id": str(quarantine.id),
                },
            )

        # Remove sharing blocks
        sharing_blocks = ModerationAction.objects.filter(
            content_scan=content_scan,
            action_type=ActionType.BLOCK_SHARING,
            action_status__in=[ModerationStatus.PENDING, ModerationStatus.APPROVED],
        )

        for block in sharing_blocks:
            block.action_status = ModerationStatus.APPROVED  # Mark as resolved
            block.reviewed_by = admin_user
            block.action_data.update(
                {
                    "sharing_restored": True,
                    "restored_by": admin_user.username,
                    "restored_at": timezone.now().isoformat(),
                }
            )
            block.save()


# Global instance for easy access
admin_review_queue = AdminReviewQueue()


def get_admin_dashboard_data() -> Dict[str, Any]:
    """Get comprehensive data for admin moderation dashboard"""

    queue_stats = admin_review_queue.get_review_statistics()

    # Recent activity (last 7 days)
    week_ago = timezone.now() - timedelta(days=7)
    recent_scans = ContentScan.objects.filter(scanned_at__gte=week_ago).count()
    recent_violations = PolicyViolation.objects.filter(created_at__gte=week_ago).count()
    recent_actions = ModerationAction.objects.filter(created_at__gte=week_ago).count()

    # Top violation types
    top_violation_types = list(
        PolicyViolation.objects.filter(created_at__gte=week_ago)
        .values("violation_type")
        .annotate(count=Count("id"))
        .order_by("-count")[:5]
    )

    # User activity summary
    active_users = (
        ContentScan.objects.filter(scanned_at__gte=week_ago).values("user").distinct().count()
    )

    return {
        "review_queue": queue_stats,
        "recent_activity": {
            "scans_this_week": recent_scans,
            "violations_this_week": recent_violations,
            "actions_this_week": recent_actions,
            "active_users_this_week": active_users,
        },
        "violation_trends": {"top_violation_types": top_violation_types},
        "system_health": {
            "total_users_with_violations": PolicyViolation.objects.values("content_scan__user")
            .distinct()
            .count(),
            "avg_scan_score": ContentScan.objects.aggregate(avg_score=Count("scan_score"))[
                "avg_score"
            ]
            or 0,
            "patterns_active": ContentScan.objects.exclude(patterns_matched=[]).count(),
        },
    }


def create_admin_summary_report(days: int = 7) -> Dict[str, Any]:
    """Create comprehensive admin report for specified time period"""

    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)

    # Basic metrics
    scans_in_period = ContentScan.objects.filter(
        scanned_at__gte=start_date, scanned_at__lte=end_date
    )

    violations_in_period = PolicyViolation.objects.filter(
        created_at__gte=start_date, created_at__lte=end_date
    )

    actions_in_period = ModerationAction.objects.filter(
        created_at__gte=start_date, created_at__lte=end_date
    )

    # Generate comprehensive report
    report = {
        "period": {"start_date": start_date.date(), "end_date": end_date.date(), "days": days},
        "scanning_activity": {
            "total_scans": scans_in_period.count(),
            "avg_scan_score": scans_in_period.aggregate(avg_score=Count("scan_score"))["avg_score"]
            or 0,
            "scans_with_violations": scans_in_period.filter(violations_found__gt=0).count(),
            "unique_users_scanned": scans_in_period.values("user").distinct().count(),
        },
        "violations": {
            "total_violations": violations_in_period.count(),
            "by_severity": {
                severity: violations_in_period.filter(severity=severity).count()
                for severity in ["critical", "high", "medium", "low"]
            },
            "by_type": list(
                violations_in_period.values("violation_type")
                .annotate(count=Count("id"))
                .order_by("-count")
            ),
            "resolution_rate": _calculate_resolution_rate(violations_in_period),
        },
        "admin_actions": {
            "total_actions": actions_in_period.count(),
            "by_type": list(
                actions_in_period.values("action_type")
                .annotate(count=Count("id"))
                .order_by("-count")
            ),
            "avg_response_time_hours": _calculate_avg_response_time(actions_in_period),
        },
        "generated_at": timezone.now(),
    }

    return report


def _calculate_resolution_rate(violations_queryset) -> float:
    """Calculate percentage of resolved violations"""
    total = violations_queryset.count()
    if total == 0:
        return 100.0

    resolved = violations_queryset.filter(is_resolved=True).count()
    return round((resolved / total) * 100, 1)


def _calculate_avg_response_time(actions_queryset) -> float:
    """Calculate average response time for admin actions"""
    review_actions = actions_queryset.filter(
        action_type=ActionType.REQUIRE_REVIEW,
        action_status__in=[ModerationStatus.APPROVED, ModerationStatus.REQUIRES_REVIEW],
    ).exclude(reviewed_by=None)

    if not review_actions.exists():
        return 0.0

    total_hours = 0
    count = 0

    for action in review_actions:
        if hasattr(action, "reviewed_at") or "reviewed_at" in action.action_data:
            reviewed_at_str = action.action_data.get("reviewed_at")
            if reviewed_at_str:
                try:
                    from datetime import datetime

                    reviewed_at = datetime.fromisoformat(reviewed_at_str.replace("Z", "+00:00"))
                    response_time = reviewed_at - action.created_at.replace(
                        tzinfo=reviewed_at.tzinfo
                    )
                    total_hours += response_time.total_seconds() / 3600
                    count += 1
                except:
                    continue

    return round(total_hours / count, 1) if count > 0 else 0.0
