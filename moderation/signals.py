"""
Django signals for automated moderation workflows

Automatically triggers content scanning when content is created or updated,
implements quarantine workflows, and manages user notifications.
"""

import logging
from datetime import timedelta
from typing import Optional

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from documents.models import Document
from forum.models import Post
from messaging.models import Message

from .content_analyzer import moderation_engine
from .models import (
    ActionType,
    ContentScan,
    ModerationAction,
    ModerationSettings,
    ModerationStatus,
    PolicyViolation,
    SensitivityLevel,
)
from .notifications import send_quarantine_notification, send_violation_notification

User = get_user_model()
logger = logging.getLogger("moderation.signals")


@receiver(post_save, sender=Document)
def auto_scan_document(sender, instance, created, **kwargs):
    """Automatically scan documents when created or significantly updated"""
    if not created and not _should_rescan_document(instance):
        return

    # Check if user has auto-scanning enabled
    try:
        settings = ModerationSettings.objects.get(user=instance.owner)
        if not settings.auto_scan_enabled:
            return
    except ModerationSettings.DoesNotExist:
        # Default to enabled if no settings exist
        pass

    # Extract content to scan
    content = _extract_document_content(instance)
    if not content:
        return

    try:
        # Perform the scan
        scan_result = moderation_engine.process_content(
            content_object=instance, user=instance.owner, content=content, scan_type="automatic"
        )

        logger.info(
            f"Auto-scanned document {instance.id}: found {scan_result.get('violations_count', 0)} violations"
        )

        # Handle high-risk results
        if scan_result.get("risk_level") in ["High", "Critical"]:
            _handle_high_risk_content(instance, instance.owner, scan_result)

    except Exception as e:
        logger.error(f"Failed to auto-scan document {instance.id}: {str(e)}")


@receiver(post_save, sender=Message)
def auto_scan_message(sender, instance, created, **kwargs):
    """Automatically scan messages when sent"""
    if not created:
        return

    # Check if user has auto-scanning enabled
    try:
        settings = ModerationSettings.objects.get(user=instance.sender)
        if not settings.auto_scan_enabled:
            return
    except ModerationSettings.DoesNotExist:
        pass

    content = instance.content or ""
    if not content.strip():
        return

    try:
        scan_result = moderation_engine.process_content(
            content_object=instance, user=instance.sender, content=content, scan_type="automatic"
        )

        logger.info(
            f"Auto-scanned message {instance.id}: found {scan_result.get('violations_count', 0)} violations"
        )

        if scan_result.get("risk_level") in ["High", "Critical"]:
            _handle_high_risk_content(instance, instance.sender, scan_result)

    except Exception as e:
        logger.error(f"Failed to auto-scan message {instance.id}: {str(e)}")


@receiver(post_save, sender=Post)
def auto_scan_forum_post(sender, instance, created, **kwargs):
    """Automatically scan forum posts when created or updated"""
    if not created and not _should_rescan_post(instance):
        return

    # Check if user has auto-scanning enabled
    try:
        settings = ModerationSettings.objects.get(user=instance.author)
        if not settings.auto_scan_enabled:
            return
    except ModerationSettings.DoesNotExist:
        pass

    # Combine title and content for scanning
    content_parts = []
    if hasattr(instance, "title") and instance.title:
        content_parts.append(instance.title)
    if hasattr(instance, "content") and instance.content:
        content_parts.append(instance.content)

    content = "\n".join(content_parts).strip()
    if not content:
        return

    try:
        scan_result = moderation_engine.process_content(
            content_object=instance, user=instance.author, content=content, scan_type="automatic"
        )

        logger.info(
            f"Auto-scanned forum post {instance.id}: found {scan_result.get('violations_count', 0)} violations"
        )

        if scan_result.get("risk_level") in ["High", "Critical"]:
            _handle_high_risk_content(instance, instance.author, scan_result)

    except Exception as e:
        logger.error(f"Failed to auto-scan forum post {instance.id}: {str(e)}")


@receiver(post_save, sender=PolicyViolation)
def handle_violation_created(sender, instance, created, **kwargs):
    """Handle actions when a new policy violation is detected"""
    if not created:
        return

    user = instance.content_scan.user

    try:
        settings = ModerationSettings.objects.get(user=user)
    except ModerationSettings.DoesNotExist:
        # Create default settings if none exist
        settings = ModerationSettings.objects.create(user=user)

    # Handle critical violations with auto-quarantine
    if instance.severity == SensitivityLevel.CRITICAL and settings.auto_quarantine_critical:
        _auto_quarantine_content(instance, user)

    # Send notification if enabled
    if settings.notify_on_violations:
        try:
            send_violation_notification(user, instance)
        except Exception as e:
            logger.error(f"Failed to send violation notification to {user.username}: {str(e)}")

    # Block sharing for high-risk content if enabled
    if settings.auto_block_sharing and instance.severity in [
        SensitivityLevel.HIGH,
        SensitivityLevel.CRITICAL,
    ]:
        _block_content_sharing(instance, user)


def _should_rescan_document(document) -> bool:
    """Determine if a document should be rescanned based on changes"""
    # Check if the file was actually replaced/updated
    if not hasattr(document, "_state") or not document._state.fields_cache:
        return True

    # Check if relevant fields changed (this is a simplified check)
    # In a real implementation, you'd want to check if the file content changed
    return True  # For now, always rescan on updates


def _should_rescan_post(post) -> bool:
    """Determine if a forum post should be rescanned"""
    # Check if title or content changed
    if not hasattr(post, "_state") or not post._state.fields_cache:
        return True
    return True  # For now, always rescan on updates


def _extract_document_content(document) -> Optional[str]:
    """Extract text content from a document for scanning"""
    # This is a simplified version - in practice you'd want proper text extraction
    # for different file types (PDF, DOCX, etc.)

    try:
        if hasattr(document, "get_content") and callable(document.get_content):
            return document.get_content()
        elif hasattr(document, "content") and document.content:
            return str(document.content)
        elif hasattr(document, "description") and document.description:
            return document.description
        elif hasattr(document, "title") and document.title:
            return document.title
        else:
            return f"Document: {document.title if hasattr(document, 'title') else 'Untitled'}"
    except Exception as e:
        logger.warning(f"Could not extract content from document {document.id}: {str(e)}")
        return None


def _handle_high_risk_content(content_object, user, scan_result):
    """Handle content that was flagged as high risk"""

    try:
        settings = ModerationSettings.objects.get(user=user)
    except ModerationSettings.DoesNotExist:
        settings = ModerationSettings.objects.create(user=user)

    # Get the content scan from the result
    scan_id = scan_result.get("scan_id")
    if not scan_id:
        logger.error("No scan_id in scan_result for high-risk content handling")
        return

    try:
        content_scan = ContentScan.objects.get(id=scan_id)
    except ContentScan.DoesNotExist:
        logger.error(f"ContentScan {scan_id} not found")
        return

    # Auto-quarantine if enabled and risk is critical
    if settings.auto_quarantine_critical and scan_result.get("risk_level") == "Critical":
        _auto_quarantine_content_scan(content_scan, user)

    # Block sharing if enabled
    if settings.auto_block_sharing and scan_result.get("risk_level") in ["High", "Critical"]:
        _block_content_sharing_scan(content_scan, user)

    # Always create a review action for high-risk content
    ModerationAction.objects.create(
        content_scan=content_scan,
        action_type=ActionType.REQUIRE_REVIEW,
        action_status=ModerationStatus.PENDING,
        reason=f"High-risk content detected: {scan_result.get('risk_level')} risk level",
        automated=True,
        triggered_by=user,
        action_data={
            "risk_level": scan_result.get("risk_level"),
            "violations_count": scan_result.get("violations_count", 0),
            "auto_flagged": True,
        },
    )


def _auto_quarantine_content(violation: PolicyViolation, user):
    """Automatically quarantine content based on a policy violation"""
    content_scan = violation.content_scan
    _auto_quarantine_content_scan(content_scan, user, violation)


def _auto_quarantine_content_scan(
    content_scan: ContentScan, user, violation: Optional[PolicyViolation] = None
):
    """Quarantine content based on a content scan"""

    # Check if already quarantined
    existing_quarantine = ModerationAction.objects.filter(
        content_scan=content_scan,
        action_type=ActionType.QUARANTINE,
        action_status__in=[ModerationStatus.APPROVED, ModerationStatus.PENDING],
    ).exists()

    if existing_quarantine:
        return  # Already quarantined

    # Create quarantine action
    quarantine_days = 7  # Default quarantine period
    action = ModerationAction.objects.create(
        content_scan=content_scan,
        violation=violation,
        action_type=ActionType.QUARANTINE,
        action_status=ModerationStatus.APPROVED,  # Auto-approved
        reason="Automatic quarantine due to critical privacy violation",
        automated=True,
        triggered_by=user,
        expiry_date=timezone.now() + timedelta(days=quarantine_days),
        action_data={
            "quarantine_days": quarantine_days,
            "auto_quarantined": True,
            "violation_severity": violation.severity if violation else "critical",
        },
    )

    logger.info(f"Auto-quarantined content scan {content_scan.id} for {quarantine_days} days")

    # Send quarantine notification
    try:
        settings = ModerationSettings.objects.get(user=user)
        if settings.notify_on_quarantine:
            send_quarantine_notification(user, action)
    except ModerationSettings.DoesNotExist:
        pass  # No settings, skip notification
    except Exception as e:
        logger.error(f"Failed to send quarantine notification: {str(e)}")


def _block_content_sharing(violation: PolicyViolation, user):
    """Block sharing of content based on a policy violation"""
    content_scan = violation.content_scan
    _block_content_sharing_scan(content_scan, user, violation)


def _block_content_sharing_scan(
    content_scan: ContentScan, user, violation: Optional[PolicyViolation] = None
):
    """Block sharing of content based on a content scan"""

    # Check if sharing already blocked
    existing_block = ModerationAction.objects.filter(
        content_scan=content_scan,
        action_type=ActionType.BLOCK_SHARING,
        action_status__in=[ModerationStatus.APPROVED, ModerationStatus.PENDING],
    ).exists()

    if existing_block:
        return  # Already blocked

    # Create sharing block action
    ModerationAction.objects.create(
        content_scan=content_scan,
        violation=violation,
        action_type=ActionType.BLOCK_SHARING,
        action_status=ModerationStatus.APPROVED,  # Auto-approved
        reason="Automatic sharing block due to sensitive content detection",
        automated=True,
        triggered_by=user,
        action_data={
            "auto_blocked": True,
            "can_override": True,  # User can request override
            "violation_severity": violation.severity if violation else "high",
        },
    )

    logger.info(f"Auto-blocked sharing for content scan {content_scan.id}")


# Bulk scanning functionality
def trigger_bulk_scan_for_user(user, content_type: str = "all", max_items: int = 100):
    """
    Trigger bulk scanning for a user's existing content

    Args:
        user: User object
        content_type: 'documents', 'messages', 'posts', or 'all'
        max_items: Maximum number of items to scan
    """

    scanned_count = 0

    try:
        settings = ModerationSettings.objects.get(user=user)
    except ModerationSettings.DoesNotExist:
        # Create default settings
        settings = ModerationSettings.objects.create(user=user)

    # Get unscanned content
    if content_type in ["documents", "all"]:
        documents = _get_unscanned_documents(user, max_items - scanned_count)
        for doc in documents:
            try:
                auto_scan_document(Document, doc, created=False)
                scanned_count += 1
            except Exception as e:
                logger.error(f"Error in bulk scan of document {doc.id}: {str(e)}")

    if content_type in ["messages", "all"] and scanned_count < max_items:
        messages = _get_unscanned_messages(user, max_items - scanned_count)
        for msg in messages:
            try:
                auto_scan_message(Message, msg, created=False)
                scanned_count += 1
            except Exception as e:
                logger.error(f"Error in bulk scan of message {msg.id}: {str(e)}")

    if content_type in ["posts", "all"] and scanned_count < max_items:
        posts = _get_unscanned_posts(user, max_items - scanned_count)
        for post in posts:
            try:
                auto_scan_forum_post(Post, post, created=False)
                scanned_count += 1
            except Exception as e:
                logger.error(f"Error in bulk scan of post {post.id}: {str(e)}")

    logger.info(f"Bulk scan completed for user {user.username}: scanned {scanned_count} items")
    return scanned_count


def _get_unscanned_documents(user, limit: int):
    """Get documents that haven't been scanned recently"""
    from django.contrib.contenttypes.models import ContentType

    doc_content_type = ContentType.objects.get_for_model(Document)

    # Get documents that don't have recent scans
    scanned_doc_ids = ContentScan.objects.filter(
        user=user,
        content_type=doc_content_type,
        scanned_at__gte=timezone.now() - timedelta(days=30),  # Scanned in last 30 days
    ).values_list("object_id", flat=True)

    return (
        Document.objects.filter(owner=user)
        .exclude(id__in=scanned_doc_ids)
        .order_by("-created_at")[:limit]
    )


def _get_unscanned_messages(user, limit: int):
    """Get messages that haven't been scanned recently"""
    from django.contrib.contenttypes.models import ContentType

    msg_content_type = ContentType.objects.get_for_model(Message)

    scanned_msg_ids = ContentScan.objects.filter(
        user=user,
        content_type=msg_content_type,
        scanned_at__gte=timezone.now() - timedelta(days=30),
    ).values_list("object_id", flat=True)

    return (
        Message.objects.filter(sender=user)
        .exclude(id__in=scanned_msg_ids)
        .order_by("-created_at")[:limit]
    )


def _get_unscanned_posts(user, limit: int):
    """Get forum posts that haven't been scanned recently"""
    from django.contrib.contenttypes.models import ContentType

    post_content_type = ContentType.objects.get_for_model(Post)

    scanned_post_ids = ContentScan.objects.filter(
        user=user,
        content_type=post_content_type,
        scanned_at__gte=timezone.now() - timedelta(days=30),
    ).values_list("object_id", flat=True)

    return (
        Post.objects.filter(author=user)
        .exclude(id__in=scanned_post_ids)
        .order_by("-created_at")[:limit]
    )
