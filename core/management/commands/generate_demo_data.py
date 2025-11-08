"""
Generate realistic demo data for Data Destroyer platform.

Usage:
    python manage.py generate_demo_data
    python manage.py generate_demo_data --clean
    python manage.py generate_demo_data --users 10 --days 60
"""

import random
from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from faker import Faker

from analytics.models import AnalyticsSnapshot, DataUsageMetric, PrivacyInsight, RetentionTimeline
from discovery.models import (
    ClassificationResult,
    ClassificationRule,
    DataAsset,
    DiscoveryJob,
)
from documents.models import Document, DocumentCategory
from forum.models import ForumCategory, Post, Topic
from messaging.models import Message, MessageThread, ThreadParticipant
from moderation.models import ContentScan, ModerationSettings, PolicyViolation, SensitiveContentPattern
from profiles.models import SecuritySettings, UserProfile

fake = Faker()


class Command(BaseCommand):
    help = "Generate demo data for Data Destroyer platform"

    def add_arguments(self, parser):
        parser.add_argument(
            "--users",
            type=int,
            default=5,
            help="Number of demo users to create (default: 5)",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Number of days of historical data (default: 30)",
        )
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Clean existing demo data before generating new data",
        )

    def handle(self, *args, **options):
        num_users = options["users"]
        num_days = options["days"]
        clean = options["clean"]

        self.stdout.write(self.style.SUCCESS("🚀 Starting demo data generation..."))

        if clean:
            self.stdout.write("🧹 Cleaning existing demo data...")
            self.clean_demo_data()

        with transaction.atomic():
            # Create users
            self.stdout.write("👤 Creating demo users...")
            users = self.create_users(num_users)

            # Create document categories
            self.stdout.write("📁 Creating document categories...")
            categories = self.create_document_categories()

            # Create forum categories
            self.stdout.write("💬 Creating forum categories...")
            forum_categories = self.create_forum_categories()

            # Create moderation patterns (if not exists)
            self.stdout.write("🛡️ Ensuring moderation patterns exist...")
            self.ensure_moderation_patterns()

            # Generate data for each user
            for user in users:
                self.stdout.write(f"\n📊 Generating data for {user.username}...")

                # Documents
                self.stdout.write("  📄 Creating documents...")
                self.create_documents(user, categories, count=random.randint(8, 15))

                # Forum activity
                self.stdout.write("  💬 Creating forum posts...")
                self.create_forum_activity(user, forum_categories, count=random.randint(3, 8))

                # Messages
                self.stdout.write("  ✉️ Creating messages...")
                self.create_messages(user, users, count=random.randint(2, 5))

                # Moderation scans and violations
                self.stdout.write("  🔍 Creating content scans...")
                self.create_moderation_data(user, count=random.randint(15, 25))

                # Discovered assets
                self.stdout.write("  🔎 Creating discovered assets...")
                self.create_discovered_assets(user, count=random.randint(20, 40))

                # Analytics snapshots (historical)
                self.stdout.write(f"  📈 Creating {num_days} days of analytics...")
                self.create_analytics_snapshots(user, num_days)

                # Privacy insights
                self.stdout.write("  💡 Creating privacy insights...")
                self.create_privacy_insights(user, count=random.randint(5, 10))

                # Retention timeline
                self.stdout.write("  ⏰ Creating retention timeline...")
                self.create_retention_timeline(user)

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Demo data generation complete!\n"
                f"   Created {num_users} users with {num_days} days of data\n"
                f"   You can now login with any of these users (password: demo123)"
            )
        )

    def clean_demo_data(self):
        """Clean existing demo data"""
        # Delete users starting with 'demo_'
        User.objects.filter(username__startswith="demo_").delete()

    def create_users(self, count):
        """Create demo users with profiles"""
        users = []

        for i in range(count):
            username = f"demo_{fake.user_name()}{i}"
            email = f"demo{i}@datadestroyer.local"

            user = User.objects.create_user(
                username=username,
                email=email,
                password="demo123",
                first_name=fake.first_name(),
                last_name=fake.last_name(),
            )

            # Create profile
            UserProfile.objects.create(
                user=user,
                bio=fake.text(max_nb_chars=200),
                privacy_level=random.choice(["public", "friends", "private", "hidden"]),
                data_retention_days=random.choice([30, 60, 90, 180, 365]),
                auto_delete_messages=random.choice([True, False]),
                auto_delete_documents=random.choice([True, False]),
                anonymize_analytics=random.choice([True, False]),
            )

            # Create security settings
            SecuritySettings.objects.create(
                user=user,
                two_factor_enabled=random.choice([True, False]),
                encryption_enabled=random.choice([True, True, False]),  # Bias toward True
                session_timeout_minutes=random.choice([30, 60, 120, 240]),
            )

            # Create moderation settings
            ModerationSettings.objects.create(
                user=user,
                auto_quarantine_critical=True,
                notification_on_violation=random.choice([True, False]),
                sensitivity_level=random.choice(["low", "medium", "high", "critical"]),
            )

            users.append(user)
            self.stdout.write(f"  ✓ Created user: {username}")

        return users

    def create_document_categories(self):
        """Create document categories"""
        categories_data = [
            ("Personal", 365, "Personal documents and files"),
            ("Financial", 2555, "Financial records and statements"),
            ("Medical", 3650, "Medical records and health information"),
            ("Legal", 3650, "Legal documents and contracts"),
            ("Work", 1825, "Work-related documents"),
        ]

        categories = []
        for name, retention_days, description in categories_data:
            category, _ = DocumentCategory.objects.get_or_create(
                name=name,
                defaults={
                    "description": description,
                    "default_retention_days": retention_days,
                },
            )
            categories.append(category)

        return categories

    def create_forum_categories(self):
        """Create forum categories"""
        categories_data = [
            ("General Discussion", "General topics and discussions"),
            ("Privacy Tips", "Tips and tricks for better privacy"),
            ("Data Security", "Discussions about data security"),
            ("Product Feedback", "Feedback and feature requests"),
        ]

        categories = []
        for name, description in categories_data:
            category, _ = ForumCategory.objects.get_or_create(
                name=name,
                defaults={
                    "description": description,
                    "default_retention_days": random.choice([90, 180, 365]),
                },
            )
            categories.append(category)

        return categories

    def ensure_moderation_patterns(self):
        """Ensure moderation patterns exist"""
        if SensitiveContentPattern.objects.count() == 0:
            self.stdout.write("  ⚠️ No moderation patterns found. Run: python manage.py load_moderation_patterns")

    def create_documents(self, user, categories, count=10):
        """Create sample documents"""
        file_types = [".pdf", ".docx", ".txt", ".xlsx", ".jpg", ".png"]

        for _ in range(count):
            file_name = fake.file_name()
            file_type = random.choice(file_types)

            document = Document.objects.create(
                owner=user,
                name=file_name,
                description=fake.sentence(),
                file=f"documents/{user.username}/{file_name}{file_type}",
                file_size=random.randint(1024, 10485760),  # 1KB to 10MB
                file_type=file_type.lstrip("."),
                category=random.choice(categories),
                is_encrypted=random.choice([True, True, False]),  # Bias toward encrypted
                encryption_type=random.choice(["AES-256", "RSA-2048", ""]) if random.random() > 0.3 else "",
                file_hash=fake.sha256(),
                password_protected=random.choice([True, False]),
                is_quarantined=random.choice([True, False]) if random.random() < 0.1 else False,
            )

            # Set retention date for some documents
            if random.random() > 0.5:
                days_until_deletion = random.randint(30, 365)
                document.retention_date = timezone.now() + timedelta(days=days_until_deletion)
                document.save()

    def create_forum_activity(self, user, categories, count=5):
        """Create forum topics and posts"""
        for _ in range(count):
            # Create topic
            topic = Topic.objects.create(
                category=random.choice(categories),
                author=user,
                title=fake.sentence().rstrip("."),
                is_pinned=random.choice([True, False]) if random.random() < 0.1 else False,
            )

            # Create posts in topic
            num_posts = random.randint(1, 5)
            for _ in range(num_posts):
                Post.objects.create(
                    topic=topic,
                    author=user,
                    content=fake.paragraph(nb_sentences=random.randint(2, 5)),
                )

    def create_messages(self, user, all_users, count=3):
        """Create message threads and messages"""
        other_users = [u for u in all_users if u != user]

        for _ in range(count):
            if not other_users:
                break

            recipient = random.choice(other_users)

            # Create thread
            thread = MessageThread.objects.create(
                subject=fake.sentence().rstrip("."),
            )

            # Add participants
            ThreadParticipant.objects.create(user=user, thread=thread)
            ThreadParticipant.objects.create(user=recipient, thread=thread)

            # Create messages
            num_messages = random.randint(2, 8)
            for i in range(num_messages):
                sender = user if i % 2 == 0 else recipient

                Message.objects.create(
                    thread=thread,
                    sender=sender,
                    content=fake.paragraph(nb_sentences=random.randint(1, 3)),
                    is_encrypted=random.choice([True, False]),
                    encryption_type=random.choice(["AES-256", "PGP", ""]) if random.random() > 0.5 else "",
                )

    def create_moderation_data(self, user, count=20):
        """Create content scans and violations"""
        patterns = list(SensitiveContentPattern.objects.filter(is_active=True))

        if not patterns:
            self.stdout.write("    ⚠️ Skipping moderation data (no patterns found)")
            return

        # Sample sensitive data for realistic violations
        sensitive_samples = {
            "ssn": ["123-45-6789", "987-65-4321", "555-12-3456"],
            "credit_card": ["4532-1234-5678-9010", "5425-2334-3010-9903", "3782-822463-10005"],
            "email": [fake.email() for _ in range(5)],
            "phone": [fake.phone_number() for _ in range(5)],
            "medical_id": ["MRN-123456", "MED-789012", "PATIENT-345678"],
        }

        for _ in range(count):
            # Generate scan content
            has_violation = random.random() > 0.3  # 70% chance of violation

            if has_violation:
                # Pick a pattern and generate content with that sensitive data
                pattern = random.choice(patterns)
                pattern_type = pattern.name.lower()

                if "ssn" in pattern_type or "social" in pattern_type:
                    sample_data = random.choice(sensitive_samples["ssn"])
                elif "credit" in pattern_type or "card" in pattern_type:
                    sample_data = random.choice(sensitive_samples["credit_card"])
                elif "email" in pattern_type:
                    sample_data = random.choice(sensitive_samples["email"])
                elif "phone" in pattern_type:
                    sample_data = random.choice(sensitive_samples["phone"])
                elif "medical" in pattern_type or "mrn" in pattern_type:
                    sample_data = random.choice(sensitive_samples["medical_id"])
                else:
                    sample_data = fake.word()

                scanned_text = f"{fake.sentence()} {sample_data} {fake.sentence()}"
                violations_count = 1
                risk_score = random.randint(60, 100)
            else:
                scanned_text = fake.paragraph()
                violations_count = 0
                risk_score = random.randint(0, 40)

            # Create scan
            scan = ContentScan.objects.create(
                user=user,
                content_type="document",
                object_id=str(random.randint(1, 1000)),
                scanned_text=scanned_text[:500],  # Truncate for DB
                risk_score=Decimal(str(risk_score)),
                violations_count=violations_count,
                has_critical_violations=risk_score > 80,
                is_quarantined=risk_score > 90,
            )

            # Create violations if any
            if has_violation and patterns:
                pattern = random.choice(patterns)

                PolicyViolation.objects.create(
                    scan=scan,
                    pattern=pattern,
                    severity=pattern.severity,
                    matched_text=sample_data if "sample_data" in locals() else fake.word(),
                    context=scanned_text[:200],
                    position_start=random.randint(0, 100),
                    position_end=random.randint(100, 200),
                    resolution_status=random.choice(
                        ["pending", "pending", "acknowledged", "resolved", "false_positive"]
                    ),
                    resolution_notes=fake.sentence() if random.random() > 0.5 else "",
                )

    def create_discovered_assets(self, user, count=30):
        """Create discovered data assets"""
        asset_types = ["database_table", "file", "api_endpoint", "cloud_storage", "document"]
        classification_types = ["PII", "PHI", "Financial", "IP", "Confidential"]

        for _ in range(count):
            asset = DataAsset.objects.create(
                name=f"{fake.word()}_{fake.word()}",
                asset_type=random.choice(asset_types),
                description=fake.sentence(),
                location=f"/data/{fake.word()}/{fake.word()}",
                owner=user.username,
                size_bytes=random.randint(1024, 104857600),  # 1KB to 100MB
            )

            # Add classification results
            num_classifications = random.randint(1, 3)
            for _ in range(num_classifications):
                ClassificationResult.objects.create(
                    asset=asset,
                    rule=None,  # Would need to create rules
                    classification_type=random.choice(classification_types),
                    confidence_score=Decimal(str(random.uniform(0.7, 0.99))),
                    details={
                        "field_name": fake.word(),
                        "sample_count": random.randint(1, 100),
                        "algorithm": random.choice(["regex", "ml", "keyword"]),
                    },
                )

    def create_analytics_snapshots(self, user, num_days=30):
        """Create historical analytics snapshots"""
        documents = Document.objects.filter(owner=user)
        posts = Post.objects.filter(author=user)
        messages = Message.objects.filter(sender=user)
        scans = ContentScan.objects.filter(user=user)
        violations = PolicyViolation.objects.filter(scan__user=user)
        assets = DataAsset.objects.filter(owner=user.username)

        base_counts = {
            "documents": documents.count(),
            "posts": posts.count(),
            "messages": messages.count(),
        }

        # Start privacy score (random between 60-90)
        privacy_score = random.randint(60, 90)

        for days_ago in range(num_days, -1, -1):
            snapshot_date = (timezone.now() - timedelta(days=days_ago)).date()

            # Simulate gradual changes
            doc_count = max(0, base_counts["documents"] - random.randint(0, days_ago // 3))
            msg_count = max(0, base_counts["messages"] - random.randint(0, days_ago // 5))
            post_count = max(0, base_counts["posts"] - random.randint(0, days_ago // 5))

            # Simulate improving privacy score over time
            privacy_score = min(100, privacy_score + random.randint(-2, 5))

            # Count violations
            critical_violations = random.randint(0, 3) if days_ago > 20 else random.randint(0, 1)
            total_violations = critical_violations + random.randint(0, 5)
            pending_violations = max(0, total_violations - random.randint(0, total_violations))

            AnalyticsSnapshot.objects.create(
                user=user,
                snapshot_date=snapshot_date,
                document_count=doc_count,
                message_count=msg_count,
                post_count=post_count,
                storage_bytes=doc_count * random.randint(10240, 1048576),
                privacy_score=Decimal(str(privacy_score)),
                security_score=Decimal(str(random.randint(70, 95))),
                total_violations=total_violations,
                critical_violations=critical_violations,
                pending_violations=pending_violations,
                risk_score=Decimal(str(max(0, 100 - privacy_score + random.randint(-10, 10)))),
                discovered_assets=assets.count(),
                classified_pii_count=random.randint(5, 20),
                classified_phi_count=random.randint(0, 10),
            )

    def create_privacy_insights(self, user, count=8):
        """Create privacy insights"""
        insight_templates = [
            {
                "type": "alert",
                "severity": "critical",
                "title": "Critical Violation Detected",
                "message": "A document containing Social Security Numbers was detected. Please review immediately.",
            },
            {
                "type": "recommendation",
                "severity": "high",
                "title": "Enable Two-Factor Authentication",
                "message": "Protect your account by enabling two-factor authentication in security settings.",
            },
            {
                "type": "tip",
                "severity": "low",
                "title": "Regular Data Cleanup",
                "message": "Consider setting up automatic deletion for old messages and documents to reduce your data footprint.",
            },
            {
                "type": "alert",
                "severity": "medium",
                "title": "Unencrypted Documents",
                "message": f"You have {random.randint(3, 10)} unencrypted documents. Enable encryption for better security.",
            },
            {
                "type": "recommendation",
                "severity": "medium",
                "title": "Privacy Score Improvement",
                "message": "Your privacy score increased by 12 points this month. Keep up the good work!",
            },
            {
                "type": "tip",
                "severity": "low",
                "title": "Data Discovery Scan",
                "message": "Run a data discovery scan to identify sensitive information across your account.",
            },
        ]

        for _ in range(count):
            template = random.choice(insight_templates)

            PrivacyInsight.objects.create(
                user=user,
                insight_type=template["type"],
                severity=template["severity"],
                title=template["title"],
                message=template["message"],
                actionable=random.choice([True, False]),
                acknowledged=random.choice([True, True, False]),  # Bias toward acknowledged
            )

    def create_retention_timeline(self, user):
        """Create retention timeline items"""
        content_types = ["document", "message", "post"]

        for content_type in content_types:
            days_until_deletion = random.randint(30, 180)

            RetentionTimeline.objects.create(
                user=user,
                content_type=content_type,
                scheduled_deletion_date=timezone.now() + timedelta(days=days_until_deletion),
                item_count=random.randint(5, 50),
                total_size_bytes=random.randint(1048576, 104857600),  # 1MB to 100MB
            )
