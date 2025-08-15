from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
import uuid

User = get_user_model()


class DataRetentionPolicy(models.TextChoices):
    """Choices for data retention policies"""
    IMMEDIATE = 'immediate', _('Delete immediately')
    DAILY = 'daily', _('Delete after 24 hours')
    WEEKLY = 'weekly', _('Delete after 7 days')
    MONTHLY = 'monthly', _('Delete after 30 days')
    QUARTERLY = 'quarterly', _('Delete after 90 days')
    YEARLY = 'yearly', _('Delete after 365 days')
    NEVER = 'never', _('Never delete automatically')


class PrivacyLevel(models.IntegerChoices):
    """Privacy levels for user data"""
    PUBLIC = 1, _('Public')
    FRIENDS = 2, _('Friends only')
    PRIVATE = 3, _('Private')
    HIDDEN = 4, _('Hidden from all')


class UserProfile(models.Model):
    """Extended user profile with privacy and data destruction settings"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    
    # Privacy settings
    privacy_level = models.IntegerField(
        choices=PrivacyLevel.choices,
        default=PrivacyLevel.PRIVATE,
        help_text=_('Default privacy level for user data')
    )
    
    # Data retention settings
    default_retention_policy = models.CharField(
        max_length=20,
        choices=DataRetentionPolicy.choices,
        default=DataRetentionPolicy.MONTHLY,
        help_text=_('Default retention policy for user-generated content')
    )
    
    auto_delete_messages = models.BooleanField(
        default=False,
        help_text=_('Automatically delete messages after retention period')
    )
    
    auto_delete_documents = models.BooleanField(
        default=False,
        help_text=_('Automatically delete documents after retention period')
    )
    
    # Security settings
    enable_two_factor = models.BooleanField(
        default=False,
        help_text=_('Enable two-factor authentication')
    )
    
    enable_encryption = models.BooleanField(
        default=True,
        help_text=_('Enable end-to-end encryption for sensitive data')
    )
    
    # Anonymization settings
    anonymize_on_delete = models.BooleanField(
        default=True,
        help_text=_('Anonymize data instead of hard delete')
    )
    
    # Profile metadata
    bio = models.TextField(
        blank=True,
        max_length=500,
        help_text=_('User biography')
    )
    
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True,
        help_text=_('User avatar image')
    )
    
    # Tracking fields
    last_data_export = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Last time user exported their data')
    )
    
    last_data_purge = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('Last time user purged their data')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('User Profile')
        verbose_name_plural = _('User Profiles')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Profile for {self.user.username}"
    
    def schedule_data_deletion(self):
        """Schedule deletion of user data based on retention policy"""
        from exposures.models import DeletionRequest
        return DeletionRequest.objects.create(
            user=self.user,
            retention_policy=self.default_retention_policy
        )


class SecuritySettings(models.Model):
    """Advanced security settings for user accounts"""
    profile = models.OneToOneField(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='security_settings'
    )
    
    # Session settings
    session_timeout_minutes = models.IntegerField(
        default=30,
        validators=[MinValueValidator(5), MaxValueValidator(1440)],
        help_text=_('Session timeout in minutes')
    )
    
    max_sessions = models.IntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text=_('Maximum concurrent sessions allowed')
    )
    
    # IP restrictions
    allowed_ips = models.JSONField(
        default=list,
        blank=True,
        help_text=_('List of allowed IP addresses')
    )
    
    blocked_ips = models.JSONField(
        default=list,
        blank=True,
        help_text=_('List of blocked IP addresses')
    )
    
    # Security notifications
    notify_on_login = models.BooleanField(
        default=True,
        help_text=_('Send notification on successful login')
    )
    
    notify_on_failed_login = models.BooleanField(
        default=True,
        help_text=_('Send notification on failed login attempts')
    )
    
    notify_on_data_export = models.BooleanField(
        default=True,
        help_text=_('Send notification when data is exported')
    )
    
    notify_on_data_deletion = models.BooleanField(
        default=True,
        help_text=_('Send notification when data is deleted')
    )
    
    # Recovery settings
    recovery_email = models.EmailField(
        blank=True,
        help_text=_('Recovery email address')
    )
    
    recovery_phone = models.CharField(
        max_length=20,
        blank=True,
        help_text=_('Recovery phone number')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Security Settings')
        verbose_name_plural = _('Security Settings')
    
    def __str__(self):
        return f"Security settings for {self.profile.user.username}"
