import hashlib
import uuid

from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class DocumentStatus(models.TextChoices):
    """Status choices for documents"""

    ACTIVE = "active", _("Active")
    ARCHIVED = "archived", _("Archived")
    SCHEDULED_DELETE = "scheduled_delete", _("Scheduled for deletion")
    DELETED = "deleted", _("Deleted")
    QUARANTINED = "quarantined", _("Quarantined")


class EncryptionMethod(models.TextChoices):
    """Encryption methods for documents"""

    NONE = "none", _("No encryption")
    AES256 = "aes256", _("AES-256")
    RSA = "rsa", _("RSA")
    PGP = "pgp", _("PGP")


class DocumentCategory(models.Model):
    """Categories for organizing documents"""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    is_sensitive = models.BooleanField(
        default=False, help_text=_("Mark if this category contains sensitive data")
    )
    default_retention_days = models.IntegerField(
        default=90, help_text=_("Default retention period in days")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Document Category")
        verbose_name_plural = _("Document Categories")
        ordering = ["name"]

    def __str__(self):
        return self.name


class Document(models.Model):
    """Core document model with encryption and security features"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Ownership and categorization
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="documents")
    category = models.ForeignKey(
        DocumentCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="documents"
    )

    # File information
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file = models.FileField(
        upload_to="documents/%Y/%m/%d/",
        validators=[
            FileExtensionValidator(
                allowed_extensions=["pdf", "doc", "docx", "txt", "jpg", "jpeg", "png", "zip"]
            )
        ],
    )
    file_size = models.BigIntegerField(help_text=_("File size in bytes"))
    file_hash = models.CharField(max_length=64, help_text=_("SHA-256 hash of the file"))
    mime_type = models.CharField(max_length=100)

    # Security and encryption
    is_encrypted = models.BooleanField(default=False)
    encryption_method = models.CharField(
        max_length=20, choices=EncryptionMethod.choices, default=EncryptionMethod.NONE
    )
    encryption_key_id = models.CharField(
        max_length=255, blank=True, help_text=_("Reference to encryption key")
    )

    # Access control
    is_public = models.BooleanField(default=False)
    password_protected = models.BooleanField(default=False)
    password_hash = models.CharField(max_length=255, blank=True)
    shared_with = models.ManyToManyField(User, related_name="shared_documents", blank=True)

    # Status and retention
    status = models.CharField(
        max_length=20, choices=DocumentStatus.choices, default=DocumentStatus.ACTIVE
    )
    retention_date = models.DateTimeField(
        null=True, blank=True, help_text=_("Date when document should be deleted")
    )
    deletion_date = models.DateTimeField(null=True, blank=True, help_text=_("Actual deletion date"))

    # Metadata
    tags = models.JSONField(default=list, blank=True, help_text=_("List of tags"))
    metadata = models.JSONField(default=dict, blank=True, help_text=_("Additional metadata"))

    # Tracking
    download_count = models.IntegerField(default=0)
    last_accessed = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Document")
        verbose_name_plural = _("Documents")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["retention_date"]),
            models.Index(fields=["file_hash"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.owner.username})"

    def save(self, *args, **kwargs):
        """Calculate file hash and size before saving"""
        if self.file and not self.file_hash:
            hasher = hashlib.sha256()
            for chunk in self.file.chunks():
                hasher.update(chunk)
            self.file_hash = hasher.hexdigest()
            self.file_size = self.file.size
        super().save(*args, **kwargs)

    def schedule_deletion(self, days=None):
        """Schedule document for deletion"""
        if days is None:
            days = self.category.default_retention_days if self.category else 90
        self.retention_date = timezone.now() + timezone.timedelta(days=days)
        self.status = DocumentStatus.SCHEDULED_DELETE
        self.save()

    def mark_as_deleted(self):
        """Mark document as deleted without removing file"""
        self.status = DocumentStatus.DELETED
        self.deletion_date = timezone.now()
        self.save()


class DocumentAccessLog(models.Model):
    """Log all document access attempts"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="access_logs")
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="document_access_logs"
    )

    # Access details
    action = models.CharField(
        max_length=50,
        choices=[
            ("view", _("View")),
            ("download", _("Download")),
            ("edit", _("Edit")),
            ("delete", _("Delete")),
            ("share", _("Share")),
            ("unshare", _("Unshare")),
            ("encrypt", _("Encrypt")),
            ("decrypt", _("Decrypt")),
        ],
    )

    success = models.BooleanField(default=True)
    failure_reason = models.CharField(max_length=255, blank=True)

    # Request metadata
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    session_key = models.CharField(max_length=255, blank=True)

    # Timestamp
    accessed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Document Access Log")
        verbose_name_plural = _("Document Access Logs")
        ordering = ["-accessed_at"]
        indexes = [
            models.Index(fields=["document", "user"]),
            models.Index(fields=["accessed_at"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.action} - {self.document.title}"
