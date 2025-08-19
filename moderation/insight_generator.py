"""
Privacy Insight Generator for Moderation Violations

Automatically generates privacy insights for the analytics dashboard
based on content moderation violations and patterns.
"""

from datetime import timedelta
from typing import Any, Dict, List

from django.contrib.auth import get_user_model
from django.utils import timezone

from analytics.models import InsightType, PrivacyInsight, SeverityLevel

from .models import PolicyViolation, ViolationType

User = get_user_model()


class ModerationInsightGenerator:
    """Generates privacy insights from moderation violations"""

    def generate_insights_for_user(self, user) -> List[PrivacyInsight]:
        """Generate privacy insights for a specific user based on recent violations"""
        insights = []

        # Get recent unresolved violations (last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        recent_violations = PolicyViolation.objects.filter(
            content_scan__user=user, created_at__gte=week_ago, is_resolved=False
        ).select_related("content_scan", "pattern")

        if not recent_violations.exists():
            return insights

        # Group violations by type and severity
        violation_summary = self._summarize_violations(recent_violations)

        # Generate insights based on violation patterns
        insights.extend(self._generate_pii_insights(user, violation_summary))
        insights.extend(self._generate_financial_insights(user, violation_summary))
        insights.extend(self._generate_medical_insights(user, violation_summary))
        insights.extend(self._generate_sharing_insights(user, violation_summary))

        return insights

    def _summarize_violations(self, violations) -> Dict[str, Any]:
        """Summarize violations by type and severity"""
        summary = {
            "by_type": {},
            "by_severity": {},
            "total_count": violations.count(),
            "critical_count": 0,
            "high_count": 0,
        }

        for violation in violations:
            # Count by type
            v_type = violation.violation_type
            if v_type not in summary["by_type"]:
                summary["by_type"][v_type] = []
            summary["by_type"][v_type].append(violation)

            # Count by severity
            severity = violation.severity
            if severity not in summary["by_severity"]:
                summary["by_severity"][severity] = 0
            summary["by_severity"][severity] += 1

            if severity == "critical":
                summary["critical_count"] += 1
            elif severity == "high":
                summary["high_count"] += 1

        return summary

    def _generate_pii_insights(self, user, summary: Dict) -> List[PrivacyInsight]:
        """Generate insights for PII violations"""
        insights = []
        pii_violations = summary["by_type"].get(ViolationType.PII_DETECTED, [])

        if not pii_violations:
            return insights

        if len(pii_violations) >= 3:
            insights.append(
                PrivacyInsight(
                    user=user,
                    insight_type=InsightType.ALERT,
                    severity=SeverityLevel.HIGH,
                    title="Multiple PII Exposures Detected",
                    description=f"We found {len(pii_violations)} instances of personal information "
                    f"in your recent content. This includes items like Social Security numbers, "
                    f"phone numbers, or driver's license numbers.",
                    action_text="Review Content",
                    expires_at=timezone.now() + timedelta(days=30),
                )
            )
        elif len(pii_violations) == 1:
            violation = pii_violations[0]
            insights.append(
                PrivacyInsight(
                    user=user,
                    insight_type=InsightType.RECOMMENDATION,
                    severity=SeverityLevel.MEDIUM,
                    title="Personal Information Detected",
                    description=f"We detected personal information ({violation.pattern.name}) "
                    f"in your recent content. Consider reviewing if this information "
                    f"needs to be shared.",
                    action_text="Review Item",
                    expires_at=timezone.now() + timedelta(days=14),
                )
            )

        return insights

    def _generate_financial_insights(self, user, summary: Dict) -> List[PrivacyInsight]:
        """Generate insights for financial data violations"""
        insights = []
        financial_violations = summary["by_type"].get(ViolationType.FINANCIAL_DATA, [])

        if not financial_violations:
            return insights

        # Financial data is always critical
        insights.append(
            PrivacyInsight(
                user=user,
                insight_type=InsightType.ALERT,
                severity=SeverityLevel.CRITICAL,
                title="Financial Information Exposed",
                description=f"We detected {len(financial_violations)} instances of financial information "
                f"such as credit card numbers or bank account details. This poses a high "
                f"privacy risk and should be removed immediately.",
                action_text="Secure Now",
                action_url="/documents/",  # Could link to specific content
                expires_at=timezone.now() + timedelta(days=7),
            )
        )

        return insights

    def _generate_medical_insights(self, user, summary: Dict) -> List[PrivacyInsight]:
        """Generate insights for medical data violations"""
        insights = []
        medical_violations = summary["by_type"].get(ViolationType.MEDICAL_DATA, [])

        if not medical_violations:
            return insights

        insights.append(
            PrivacyInsight(
                user=user,
                insight_type=InsightType.RECOMMENDATION,
                severity=SeverityLevel.HIGH,
                title="Medical Information Privacy Alert",
                description="Medical information like insurance IDs or medical record numbers "
                "was found in your content. This information is protected under HIPAA "
                "and should be handled with extra care.",
                action_text="Review Medical Data",
                expires_at=timezone.now() + timedelta(days=21),
            )
        )

        return insights

    def _generate_sharing_insights(self, user, summary: Dict) -> List[PrivacyInsight]:
        """Generate insights about sharing sensitive content"""
        insights = []

        if summary["critical_count"] >= 2:
            insights.append(
                PrivacyInsight(
                    user=user,
                    insight_type=InsightType.TIP,
                    severity=SeverityLevel.MEDIUM,
                    title="Enable Auto-Quarantine for Critical Content",
                    description=f"You have {summary['critical_count']} critical privacy violations. "
                    f"Consider enabling automatic quarantine to prevent accidental sharing "
                    f"of sensitive information.",
                    action_text="Enable Auto-Quarantine",
                    action_url="/settings/privacy/",
                    expires_at=timezone.now() + timedelta(days=30),
                )
            )

        return insights


def generate_moderation_insights(user) -> int:
    """
    Generate privacy insights for a user based on their moderation violations.

    Returns:
        Number of insights created
    """
    generator = ModerationInsightGenerator()
    insights = generator.generate_insights_for_user(user)

    created_count = 0
    for insight in insights:
        # Check if similar insight already exists (avoid duplicates)
        existing = PrivacyInsight.objects.filter(
            user=user,
            title=insight.title,
            is_dismissed=False,
            created_at__gte=timezone.now() - timedelta(days=7),
        ).exists()

        if not existing:
            insight.save()
            created_count += 1

    return created_count


def generate_insights_for_all_users() -> Dict[str, int]:
    """
    Generate insights for all users who have recent moderation violations.

    Returns:
        Dictionary with statistics about insights created
    """
    stats = {"users_processed": 0, "insights_created": 0, "users_with_violations": 0}

    # Get users with recent violations
    week_ago = timezone.now() - timedelta(days=7)
    users_with_violations = User.objects.filter(
        content_scans__violations__created_at__gte=week_ago,
        content_scans__violations__is_resolved=False,
    ).distinct()

    stats["users_with_violations"] = users_with_violations.count()

    for user in users_with_violations:
        insights_created = generate_moderation_insights(user)
        stats["insights_created"] += insights_created
        stats["users_processed"] += 1

    return stats
