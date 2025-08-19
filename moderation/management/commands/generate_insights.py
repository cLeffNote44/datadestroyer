"""
Management command to generate privacy insights from moderation violations.

This can be run periodically (e.g., via cron job) to automatically generate
insights for users based on their content moderation violations.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from moderation.insight_generator import (
    generate_insights_for_all_users,
    generate_moderation_insights,
)

User = get_user_model()


class Command(BaseCommand):
    help = "Generate privacy insights from moderation violations for all users or specific users"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user", type=str, help="Generate insights for a specific user (by username or email)"
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Generate insights for all users with recent violations",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be generated without actually creating insights",
        )

    def handle(self, *args, **options):
        if options["user"]:
            self.generate_for_user(options["user"], options.get("dry_run", False))
        elif options["all"]:
            self.generate_for_all_users(options.get("dry_run", False))
        else:
            self.stdout.write(self.style.ERROR("Please specify either --user <username> or --all"))

    def generate_for_user(self, user_identifier: str, dry_run: bool):
        """Generate insights for a specific user"""
        try:
            # Try to find user by username first, then by email
            try:
                user = User.objects.get(username=user_identifier)
            except User.DoesNotExist:
                user = User.objects.get(email=user_identifier)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User "{user_identifier}" not found'))
            return

        self.stdout.write(f"Generating insights for user: {user.username}")

        if dry_run:
            from moderation.insight_generator import ModerationInsightGenerator

            generator = ModerationInsightGenerator()
            insights = generator.generate_insights_for_user(user)

            self.stdout.write(f"Would generate {len(insights)} insights:")
            for insight in insights:
                self.stdout.write(f"  - {insight.title} ({insight.severity})")
        else:
            insights_created = generate_moderation_insights(user)
            self.stdout.write(
                self.style.SUCCESS(f"Created {insights_created} new insights for {user.username}")
            )

    def generate_for_all_users(self, dry_run: bool):
        """Generate insights for all users with recent violations"""
        self.stdout.write("Generating insights for all users with recent violations...")

        if dry_run:
            from datetime import timedelta

            from django.utils import timezone

            week_ago = timezone.now() - timedelta(days=7)
            users_with_violations = User.objects.filter(
                content_scans__violations__created_at__gte=week_ago,
                content_scans__violations__is_resolved=False,
            ).distinct()

            self.stdout.write(f"Would process {users_with_violations.count()} users:")

            for user in users_with_violations[:10]:  # Show first 10
                from moderation.insight_generator import ModerationInsightGenerator

                generator = ModerationInsightGenerator()
                insights = generator.generate_insights_for_user(user)
                self.stdout.write(f"  - {user.username}: {len(insights)} insights")

            if users_with_violations.count() > 10:
                self.stdout.write(f"  ... and {users_with_violations.count() - 10} more users")
        else:
            stats = generate_insights_for_all_users()

            self.stdout.write(
                self.style.SUCCESS(
                    f"Insight generation completed:\n"
                    f'  Users with violations: {stats["users_with_violations"]}\n'
                    f'  Users processed: {stats["users_processed"]}\n'
                    f'  Insights created: {stats["insights_created"]}'
                )
            )
