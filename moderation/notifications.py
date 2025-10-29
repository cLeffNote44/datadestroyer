"""
Notification system for moderation violations and actions

Handles sending notifications to users when violations are detected,
content is quarantined, or manual review is required.
"""

import logging
from typing import Any, Dict

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from analytics.models import InsightType, PrivacyInsight, SeverityLevel

from .models import ModerationAction, ModerationSettings, PolicyViolation

User = get_user_model()
logger = logging.getLogger("moderation.notifications")


def send_violation_notification(user, violation: PolicyViolation):
    """
    Send notification to user about a policy violation

    Args:
        user: User object
        violation: PolicyViolation instance
    """
    try:
        settings_obj = ModerationSettings.objects.get(user=user)
    except ModerationSettings.DoesNotExist:
        # Default to notifications enabled
        settings_obj = ModerationSettings.objects.create(user=user)

    if not settings_obj.notify_on_violations:
        return

    # Create privacy insight for the violation
    _create_violation_insight(user, violation)

    # Send email if enabled
    if settings_obj.email_notifications:
        _send_violation_email(user, violation)

    logger.info(f"Sent violation notification to {user.username} for violation {violation.id}")


def send_quarantine_notification(user, action: ModerationAction):
    """
    Send notification to user about content quarantine

    Args:
        user: User object
        action: ModerationAction instance (quarantine action)
    """
    try:
        settings_obj = ModerationSettings.objects.get(user=user)
    except ModerationSettings.DoesNotExist:
        settings_obj = ModerationSettings.objects.create(user=user)

    if not settings_obj.notify_on_quarantine:
        return

    # Create privacy insight for the quarantine
    _create_quarantine_insight(user, action)

    # Send email if enabled
    if settings_obj.email_notifications:
        _send_quarantine_email(user, action)

    logger.info(f"Sent quarantine notification to {user.username} for action {action.id}")


def send_review_required_notification(user, action: ModerationAction):
    """
    Send notification that manual review is required

    Args:
        user: User object
        action: ModerationAction instance (review required)
    """
    # Create privacy insight for manual review requirement
    _create_review_insight(user, action)

    try:
        settings_obj = ModerationSettings.objects.get(user=user)
        if settings_obj.email_notifications:
            _send_review_email(user, action)
    except ModerationSettings.DoesNotExist:
        pass

    logger.info(f"Sent review required notification to {user.username} for action {action.id}")


def send_bulk_scan_complete_notification(user, scan_stats: Dict[str, Any]):
    """
    Send notification when bulk scanning is complete

    Args:
        user: User object
        scan_stats: Dictionary with scan statistics
    """
    total_scanned = scan_stats.get("total_scanned", 0)
    violations_found = scan_stats.get("violations_found", 0)
    critical_violations = scan_stats.get("critical_violations", 0)

    if violations_found > 0:
        severity = SeverityLevel.CRITICAL if critical_violations > 0 else SeverityLevel.HIGH

        # Create summary insight
        PrivacyInsight.objects.create(
            user=user,
            insight_type=InsightType.ALERT,
            severity=severity,
            title="Bulk Scan Complete - Violations Found",
            description=(
                f"Your bulk content scan is complete. We scanned {total_scanned} items "
                f"and found {violations_found} privacy violations, including "
                f"{critical_violations} critical violations that need immediate attention."
            ),
            action_text="Review Results",
            action_url="/moderation/violations/",
            context_data={
                "source": "bulk_scan_complete",
                "total_scanned": total_scanned,
                "violations_found": violations_found,
                "critical_violations": critical_violations,
            },
            expires_at=timezone.now() + timezone.timedelta(days=14),
        )

        logger.info(f"Created bulk scan summary insight for {user.username}")


def _create_violation_insight(user, violation: PolicyViolation):
    """Create a privacy insight for a policy violation"""

    # Map violation types to user-friendly descriptions
    violation_descriptions = {
        "pii_detected": "Personal information like SSN or phone numbers",
        "financial_data": "Financial information like credit cards or bank accounts",
        "medical_data": "Medical information protected under HIPAA",
        "legal_data": "Legal documents or attorney-client privileged content",
        "custom_pattern": "Custom sensitive patterns you've configured",
        "bulk_sharing": "Bulk sharing of sensitive information",
    }

    description = violation_descriptions.get(
        violation.violation_type, "Sensitive content that requires attention"
    )

    severity_map = {
        "low": SeverityLevel.LOW,
        "medium": SeverityLevel.MEDIUM,
        "high": SeverityLevel.HIGH,
        "critical": SeverityLevel.CRITICAL,
    }

    insight_severity = severity_map.get(violation.severity, SeverityLevel.MEDIUM)

    # Don't create duplicate insights
    existing = PrivacyInsight.objects.filter(
        user=user, context_data__violation_id=str(violation.id), is_dismissed=False
    ).exists()

    if existing:
        return

    PrivacyInsight.objects.create(
        user=user,
        insight_type=InsightType.ALERT,
        severity=insight_severity,
        title=f"{violation.get_violation_type_display()} Detected",
        description=(
            f"We detected {description} in your content. "
            f"Pattern matched: {violation.pattern.name}. "
            f"Please review this content to ensure your privacy is protected."
        ),
        action_text="Review Content",
        action_url=f"/moderation/violations/{violation.id}/",
        context_data={
            "violation_id": str(violation.id),
            "violation_type": violation.violation_type,
            "pattern_name": violation.pattern.name,
            "source": "violation_detection",
        },
        expires_at=timezone.now() + timezone.timedelta(days=30),
    )


def _create_quarantine_insight(user, action: ModerationAction):
    """Create a privacy insight for quarantine action"""

    expiry_days = action.action_data.get("quarantine_days", 7)

    PrivacyInsight.objects.create(
        user=user,
        insight_type=InsightType.ALERT,
        severity=SeverityLevel.HIGH,
        title="Content Quarantined for Privacy Protection",
        description=(
            f"Your content has been automatically quarantined for {expiry_days} days "
            f"due to detection of sensitive information. During quarantine, this content "
            f"cannot be shared or accessed by others. You can request early release "
            f"after reviewing the privacy concerns."
        ),
        action_text="Review Quarantine",
        action_url=f"/moderation/actions/{action.id}/",
        context_data={
            "action_id": str(action.id),
            "action_type": action.action_type,
            "quarantine_days": expiry_days,
            "auto_quarantined": action.action_data.get("auto_quarantined", False),
            "source": "quarantine_action",
        },
        expires_at=action.expiry_date,
    )


def _create_review_insight(user, action: ModerationAction):
    """Create a privacy insight for manual review requirement"""

    risk_level = action.action_data.get("risk_level", "Unknown")
    violations_count = action.action_data.get("violations_count", 0)

    PrivacyInsight.objects.create(
        user=user,
        insight_type=InsightType.RECOMMENDATION,
        severity=SeverityLevel.MEDIUM,
        title="Manual Review Required",
        description=(
            f"Your content has been flagged for manual review due to {risk_level.lower()} "
            f"privacy risk with {violations_count} violation(s) detected. "
            f"Please review the content and take appropriate action to protect "
            f"your privacy and comply with data protection policies."
        ),
        action_text="Review Content",
        action_url=f"/moderation/actions/{action.id}/",
        context_data={
            "action_id": str(action.id),
            "risk_level": risk_level,
            "violations_count": violations_count,
            "auto_flagged": action.action_data.get("auto_flagged", False),
            "source": "review_required",
        },
        expires_at=timezone.now() + timezone.timedelta(days=21),
    )


def _send_violation_email(user, violation: PolicyViolation):
    """Send email notification for policy violation"""

    subject = f"Privacy Violation Detected - {violation.get_violation_type_display()}"

    context = {
        "user": user,
        "violation": violation,
        "pattern_name": violation.pattern.name,
        "severity": violation.get_severity_display(),
        "violation_type": violation.get_violation_type_display(),
        "scan_date": violation.content_scan.scanned_at,
        "dashboard_url": (
            f"{settings.BASE_URL}/analytics/dashboard/" if hasattr(settings, "BASE_URL") else "#"
        ),
    }

    # Use a basic template or plain text if templates don't exist
    try:
        html_message = render_to_string("moderation/emails/violation_notification.html", context)
        text_message = render_to_string("moderation/emails/violation_notification.txt", context)
    except:
        # Fallback to plain text
        text_message = f"""
Privacy Violation Detected

Hello {user.get_full_name() or user.username},

We detected a privacy violation in your content:

Type: {violation.get_violation_type_display()}
Severity: {violation.get_severity_display()}
Pattern: {violation.pattern.name}
Detected: {violation.content_scan.scanned_at.strftime('%Y-%m-%d %H:%M')}

Please review your content and take appropriate action to protect your privacy.

Best regards,
Data Detective Privacy Team
        """
        html_message = None

    try:
        send_mail(
            subject=subject,
            message=text_message,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@datadetective.com"),
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Sent violation email to {user.email}")
    except Exception as e:
        logger.error(f"Failed to send violation email to {user.email}: {str(e)}")


def _send_quarantine_email(user, action: ModerationAction):
    """Send email notification for quarantine action"""

    expiry_date = action.expiry_date
    quarantine_days = action.action_data.get("quarantine_days", 7)

    subject = "Content Quarantined for Privacy Protection"

    context = {
        "user": user,
        "action": action,
        "expiry_date": expiry_date,
        "quarantine_days": quarantine_days,
        "content_scan": action.content_scan,
        "dashboard_url": (
            f"{settings.BASE_URL}/analytics/dashboard/" if hasattr(settings, "BASE_URL") else "#"
        ),
    }

    # Fallback to plain text
    text_message = f"""
Content Quarantined

Hello {user.get_full_name() or user.username},

Your content has been automatically quarantined for privacy protection.

Quarantine Period: {quarantine_days} days
Release Date: {expiry_date.strftime('%Y-%m-%d %H:%M') if expiry_date else 'Manual review required'}
Reason: {action.reason}

During quarantine, this content cannot be shared or accessed by others. You can request early release after reviewing the privacy concerns.

Please visit your dashboard to review and manage quarantined content.

Best regards,
Data Detective Privacy Team
    """

    try:
        send_mail(
            subject=subject,
            message=text_message,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@datadetective.com"),
            recipient_list=[user.email],
            fail_silently=False,
        )
        logger.info(f"Sent quarantine email to {user.email}")
    except Exception as e:
        logger.error(f"Failed to send quarantine email to {user.email}: {str(e)}")


def _send_review_email(user, action: ModerationAction):
    """Send email notification for manual review requirement"""

    subject = "Manual Review Required for Your Content"
    risk_level = action.action_data.get("risk_level", "Unknown")

    text_message = f"""
Manual Review Required

Hello {user.get_full_name() or user.username},

Your content has been flagged for manual review due to potential privacy concerns.

Risk Level: {risk_level}
Detected: {action.created_at.strftime('%Y-%m-%d %H:%M')}
Reason: {action.reason}

Please review your content and take appropriate action to ensure privacy compliance.

Visit your dashboard to review the flagged content and resolve any issues.

Best regards,
Data Detective Privacy Team
    """

    try:
        send_mail(
            subject=subject,
            message=text_message,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@datadetective.com"),
            recipient_list=[user.email],
            fail_silently=False,
        )
        logger.info(f"Sent review email to {user.email}")
    except Exception as e:
        logger.error(f"Failed to send review email to {user.email}: {str(e)}")


# Admin notification functions for staff/admin users
def notify_admin_bulk_violations(violations_summary: Dict[str, Any]):
    """Notify administrators about bulk violations detected across users"""

    if not getattr(settings, "ADMIN_NOTIFICATION_EMAIL", None):
        return

    critical_violations = violations_summary.get("critical_violations", 0)
    total_violations = violations_summary.get("total_violations", 0)
    affected_users = violations_summary.get("affected_users", 0)

    if critical_violations == 0 and total_violations < 10:
        return  # Don't spam admins with minor issues

    subject = f"Privacy Alert: {critical_violations} Critical Violations Detected"

    message = f"""
Privacy Violation Summary

Critical violations detected across the platform:

- Critical violations: {critical_violations}
- Total violations: {total_violations}
- Affected users: {affected_users}
- Time period: Last 24 hours

Please review the admin dashboard for detailed information and take appropriate action.

This is an automated notification from the Data Detective privacy monitoring system.
    """

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@datadetective.com"),
            recipient_list=[settings.ADMIN_NOTIFICATION_EMAIL],
            fail_silently=True,
        )
        logger.info("Sent bulk violation summary to administrators")
    except Exception as e:
        logger.error(f"Failed to send admin notification: {str(e)}")


def create_system_insight(
    title: str,
    description: str,
    severity: str = "medium",
    action_text: str = None,
    action_url: str = None,
):
    """
    Create a system-wide insight that appears for all users

    Args:
        title: Insight title
        description: Insight description
        severity: Severity level ('low', 'medium', 'high', 'critical')
        action_text: Optional action button text
        action_url: Optional action URL
    """
    severity_map = {
        "low": SeverityLevel.LOW,
        "medium": SeverityLevel.MEDIUM,
        "high": SeverityLevel.HIGH,
        "critical": SeverityLevel.CRITICAL,
    }

    # This would typically be sent to all users or a subset
    # For now, we'll create a function that can be called to create system insights
    logger.info(f"System insight created: {title} ({severity})")

    # In a real implementation, you might want to:
    # 1. Create insights for all active users
    # 2. Use a message queue to handle bulk creation
    # 3. Store system insights separately and display them globally

    return {
        "title": title,
        "description": description,
        "severity": severity,
        "action_text": action_text,
        "action_url": action_url,
        "created_at": timezone.now(),
    }
