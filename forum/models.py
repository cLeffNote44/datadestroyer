from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid

User = get_user_model()


class TopicStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    LOCKED = "locked", _("Locked")
    ARCHIVED = "archived", _("Archived")


class PostStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    EDITED = "edited", _("Edited")
    SCHEDULED_DELETE = "scheduled_delete", _("Scheduled for deletion")
    DELETED = "deleted", _("Deleted")


class ForumCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    is_sensitive = models.BooleanField(default=False)
    default_retention_days = models.PositiveIntegerField(default=365)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Topic(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(ForumCategory, on_delete=models.CASCADE, related_name="topics")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="topics")
    title = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=TopicStatus.choices, default=TopicStatus.ACTIVE)

    retention_date = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["category", "updated_at"]),
            models.Index(fields=["author", "created_at"]),
        ]

    def __str__(self):
        return self.title

    def schedule_deletion(self, days: int = 365):
        self.retention_date = timezone.now() + timezone.timedelta(days=days)
        self.save(update_fields=["retention_date", "updated_at"])


class Post(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="posts")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts")

    content = models.TextField()
    status = models.CharField(max_length=20, choices=PostStatus.choices, default=PostStatus.ACTIVE)

    retention_date = models.DateTimeField(null=True, blank=True)
    deletion_date = models.DateTimeField(null=True, blank=True)
    edited_at = models.DateTimeField(null=True, blank=True)

    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["topic", "created_at"]),
            models.Index(fields=["author", "status"]),
            models.Index(fields=["retention_date"]),
        ]

    def __str__(self):
        return f"Post by {self.author} in {self.topic}"

    def schedule_deletion(self, days: int = 365):
        self.retention_date = timezone.now() + timezone.timedelta(days=days)
        self.status = PostStatus.SCHEDULED_DELETE
        self.save(update_fields=["retention_date", "status", "updated_at"])

    def mark_as_deleted(self):
        self.status = PostStatus.DELETED
        self.deletion_date = timezone.now()
        self.save(update_fields=["status", "deletion_date", "updated_at"])
