from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid

User = get_user_model()


class MessageStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    SCHEDULED_DELETE = "scheduled_delete", _("Scheduled for deletion")
    DELETED = "deleted", _("Deleted")


class EncryptionMethod(models.TextChoices):
    NONE = "none", _("No encryption")
    AES256 = "aes256", _("AES-256")
    PGP = "pgp", _("PGP")


class MessageThread(models.Model):
    """A conversation between two or more users."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_threads")
    participants = models.ManyToManyField(User, through="ThreadParticipant", related_name="message_threads")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.subject or f"Thread {self.pk}"


class ThreadParticipant(models.Model):
    thread = models.ForeignKey(MessageThread, on_delete=models.CASCADE, related_name="thread_participants")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="thread_participations")
    joined_at = models.DateTimeField(auto_now_add=True)
    muted = models.BooleanField(default=False)
    last_read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("thread", "user")


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thread = models.ForeignKey(MessageThread, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")

    # Optional direct recipient hint for 1:1 threads; for group threads it's implied by participants
    recipient = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="received_messages")

    content = models.TextField()
    is_encrypted = models.BooleanField(default=False)
    encryption_method = models.CharField(max_length=20, choices=EncryptionMethod.choices, default=EncryptionMethod.NONE)

    status = models.CharField(max_length=20, choices=MessageStatus.choices, default=MessageStatus.ACTIVE)
    retention_date = models.DateTimeField(null=True, blank=True)
    deletion_date = models.DateTimeField(null=True, blank=True)

    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["thread", "created_at"]),
            models.Index(fields=["sender", "status"]),
            models.Index(fields=["retention_date"]),
        ]

    def __str__(self):
        return f"{self.sender}: {self.content[:30]}"

    def schedule_deletion(self, days: int = 30):
        self.retention_date = timezone.now() + timezone.timedelta(days=days)
        self.status = MessageStatus.SCHEDULED_DELETE
        self.save(update_fields=["retention_date", "status", "updated_at"])

    def mark_as_deleted(self):
        self.status = MessageStatus.DELETED
        self.deletion_date = timezone.now()
        self.save(update_fields=["status", "deletion_date", "updated_at"])
