from django.contrib import admin

from .models import SecuritySettings, UserProfile


def _has_field(model, name: str) -> bool:
    try:
        model._meta.get_field(name)
        return True
    except Exception:
        return False


class SecuritySettingsInline(admin.StackedInline):
    model = SecuritySettings
    can_delete = False
    extra = 0

    def get_readonly_fields(self, request, obj=None):
        candidates = [
            "created_at",
            "updated_at",
            "last_updated",
            "last_password_change",
            "last_2fa_enrollment",
            "failed_login_attempts",
        ]
        return tuple([f for f in candidates if _has_field(self.model, f)])


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    inlines = [SecuritySettingsInline]
    search_fields = ("user__username", "user__email")

    def get_list_display(self, request):
        preferred = [
            "user",
            "privacy_level",
            "default_retention_policy",
            "enable_two_factor",
            "enable_encryption",
            "created_at",
        ]
        return tuple([f for f in preferred if _has_field(self.model, f) or f == "user"])

    def get_list_filter(self, request):
        preferred = [
            "privacy_level",
            "default_retention_policy",
            "enable_two_factor",
            "enable_encryption",
        ]
        return tuple([f for f in preferred if _has_field(self.model, f)])

    def get_readonly_fields(self, request, obj=None):
        ts = []
        for name in ["created_at", "updated_at", "last_data_export", "last_data_purge"]:
            if _has_field(self.model, name):
                ts.append(name)
        return tuple(ts)
