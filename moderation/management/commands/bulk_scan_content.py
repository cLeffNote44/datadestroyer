"""
Django management command for bulk scanning user content

Usage:
  python manage.py bulk_scan_content --user username
  python manage.py bulk_scan_content --all-users
  python manage.py bulk_scan_content --user username --content-type documents
"""

import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from moderation.models import ContentScan, PolicyViolation
from moderation.notifications import send_bulk_scan_complete_notification
from moderation.signals import trigger_bulk_scan_for_user

User = get_user_model()
logger = logging.getLogger("moderation.bulk_scan")


class Command(BaseCommand):
    help = "Perform bulk scanning of user content for privacy violations"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user",
            type=str,
            help="Username to scan content for (specific user)",
        )

        parser.add_argument(
            "--all-users",
            action="store_true",
            help="Scan content for all users",
        )

        parser.add_argument(
            "--content-type",
            type=str,
            choices=["documents", "messages", "posts", "all"],
            default="all",
            help="Type of content to scan (default: all)",
        )

        parser.add_argument(
            "--max-items",
            type=int,
            default=100,
            help="Maximum number of items to scan per user (default: 100)",
        )

        parser.add_argument(
            "--max-users",
            type=int,
            default=50,
            help="Maximum number of users to process when using --all-users (default: 50)",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be scanned without actually scanning",
        )

        parser.add_argument(
            "--notify",
            action="store_true",
            help="Send notifications to users when scan is complete",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting bulk content scanning..."))

        users_to_scan = self._get_users_to_scan(options)

        if not users_to_scan:
            raise CommandError("No users found to scan")

        self.stdout.write(f"Found {len(users_to_scan)} users to scan")

        if options["dry_run"]:
            self._perform_dry_run(users_to_scan, options)
            return

        total_scanned = 0
        total_violations = 0
        users_with_violations = 0

        for i, user in enumerate(users_to_scan, 1):
            self.stdout.write(f"[{i}/{len(users_to_scan)}] Scanning content for {user.username}...")

            try:
                scanned_count = trigger_bulk_scan_for_user(
                    user=user, content_type=options["content_type"], max_items=options["max_items"]
                )

                # Get violation stats for this user
                user_violations = self._get_user_violation_stats(user)

                total_scanned += scanned_count
                total_violations += user_violations["total_violations"]

                if user_violations["violations_found"] > 0:
                    users_with_violations += 1

                    self.stdout.write(
                        self.style.WARNING(
                            f"  → Scanned {scanned_count} items, "
                            f"found {user_violations['violations_found']} violations "
                            f"({user_violations['critical_violations']} critical)"
                        )
                    )

                    # Send notification if requested
                    if options["notify"]:
                        try:
                            send_bulk_scan_complete_notification(
                                user,
                                {
                                    "total_scanned": scanned_count,
                                    "violations_found": user_violations["violations_found"],
                                    "critical_violations": user_violations["critical_violations"],
                                },
                            )
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f"  → Failed to send notification: {str(e)}")
                            )
                else:
                    self.stdout.write(f"  → Scanned {scanned_count} items, no violations found")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  → Error scanning {user.username}: {str(e)}"))
                logger.error(f"Bulk scan error for {user.username}: {str(e)}")

        # Print summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Bulk scanning completed!"))
        self.stdout.write(f"Users processed: {len(users_to_scan)}")
        self.stdout.write(f"Total items scanned: {total_scanned}")
        self.stdout.write(f"Total violations found: {total_violations}")
        self.stdout.write(f"Users with violations: {users_with_violations}")

        if total_violations > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"\n⚠️  {total_violations} privacy violations were detected. "
                    f"Users should review their content for sensitive information."
                )
            )

    def _get_users_to_scan(self, options):
        """Get list of users to scan based on command options"""
        if options["user"]:
            try:
                user = User.objects.get(username=options["user"])
                return [user]
            except User.DoesNotExist:
                raise CommandError(f"User '{options['user']}' not found")

        elif options["all_users"]:
            # Get active users (logged in within last 30 days)
            thirty_days_ago = timezone.now() - timedelta(days=30)
            users = User.objects.filter(last_login__gte=thirty_days_ago, is_active=True).order_by(
                "-last_login"
            )[: options["max_users"]]

            return list(users)

        else:
            raise CommandError("Must specify either --user or --all-users")

    def _perform_dry_run(self, users_to_scan, options):
        """Perform a dry run to show what would be scanned"""
        self.stdout.write(self.style.WARNING("DRY RUN - No actual scanning will be performed"))

        from moderation.signals import (
            _get_unscanned_documents,
            _get_unscanned_messages,
            _get_unscanned_posts,
        )

        content_type = options["content_type"]
        max_items = options["max_items"]

        total_items = 0

        for user in users_to_scan:
            user_items = 0

            if content_type in ["documents", "all"]:
                docs = _get_unscanned_documents(user, max_items)
                doc_count = len(docs)
                user_items += doc_count
                if doc_count > 0:
                    self.stdout.write(f"  {user.username}: {doc_count} documents")

            if content_type in ["messages", "all"] and user_items < max_items:
                msgs = _get_unscanned_messages(user, max_items - user_items)
                msg_count = len(msgs)
                user_items += msg_count
                if msg_count > 0:
                    self.stdout.write(f"  {user.username}: {msg_count} messages")

            if content_type in ["posts", "all"] and user_items < max_items:
                posts = _get_unscanned_posts(user, max_items - user_items)
                post_count = len(posts)
                user_items += post_count
                if post_count > 0:
                    self.stdout.write(f"  {user.username}: {post_count} posts")

            if user_items > 0:
                self.stdout.write(f"  {user.username}: {user_items} items total")
            else:
                self.stdout.write(f"  {user.username}: No unscanned items")

            total_items += user_items

        self.stdout.write("\n" + "=" * 40)
        self.stdout.write(f"Total items that would be scanned: {total_items}")

    def _get_user_violation_stats(self, user):
        """Get recent violation statistics for a user"""
        # Get violations from the last scan session (last hour)
        recent_threshold = timezone.now() - timedelta(hours=1)

        recent_scans = ContentScan.objects.filter(user=user, scanned_at__gte=recent_threshold)

        recent_violations = PolicyViolation.objects.filter(content_scan__in=recent_scans)

        total_violations = recent_violations.count()
        critical_violations = recent_violations.filter(severity="critical").count()

        return {
            "violations_found": total_violations,
            "critical_violations": critical_violations,
            "total_violations": total_violations,  # Same as violations_found for recent scans
        }


# Additional utility functions that can be called from other management commands
def scan_user_content(
    username: str, content_type: str = "all", max_items: int = 100, notify: bool = False
):
    """
    Utility function to scan content for a specific user

    Args:
        username: Username to scan
        content_type: Type of content ('documents', 'messages', 'posts', 'all')
        max_items: Maximum items to scan
        notify: Whether to send notification when complete

    Returns:
        Dict with scan results
    """
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return {"error": f"User '{username}' not found"}

    try:
        scanned_count = trigger_bulk_scan_for_user(
            user=user, content_type=content_type, max_items=max_items
        )

        # Get violation stats
        recent_threshold = timezone.now() - timedelta(hours=1)
        recent_scans = ContentScan.objects.filter(user=user, scanned_at__gte=recent_threshold)
        recent_violations = PolicyViolation.objects.filter(content_scan__in=recent_scans)

        violations_found = recent_violations.count()
        critical_violations = recent_violations.filter(severity="critical").count()

        # Send notification if requested and violations found
        if notify and violations_found > 0:
            send_bulk_scan_complete_notification(
                user,
                {
                    "total_scanned": scanned_count,
                    "violations_found": violations_found,
                    "critical_violations": critical_violations,
                },
            )

        return {
            "success": True,
            "user": username,
            "scanned_count": scanned_count,
            "violations_found": violations_found,
            "critical_violations": critical_violations,
        }

    except Exception as e:
        logger.error(f"Error scanning content for {username}: {str(e)}")
        return {"error": str(e)}


def get_scan_summary():
    """Get a summary of all scanning activity"""
    total_scans = ContentScan.objects.count()
    total_violations = PolicyViolation.objects.count()
    critical_violations = PolicyViolation.objects.filter(severity="critical").count()

    # Recent activity (last 24 hours)
    recent_threshold = timezone.now() - timedelta(hours=24)
    recent_scans = ContentScan.objects.filter(scanned_at__gte=recent_threshold).count()
    recent_violations = PolicyViolation.objects.filter(created_at__gte=recent_threshold).count()

    return {
        "total_scans": total_scans,
        "total_violations": total_violations,
        "critical_violations": critical_violations,
        "recent_scans_24h": recent_scans,
        "recent_violations_24h": recent_violations,
        "last_updated": timezone.now(),
    }
