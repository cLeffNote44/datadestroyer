from django.contrib import admin

from .models import DataExportRequest, DeletionRequest, ExposureIncident, PurgeJob, RetentionPolicy


def _has_field(model, name: str) -> bool:
    try:
        model._meta.get_field(name)
        return True
    except Exception:
        return False


def _available(model, names):
    return [n for n in names if _has_field(model, n)]


class ReadonlyTimestampsMixin:
    def get_readonly_fields(self, request, obj=None):
        candidates = [
            "created_at",
            "updated_at",
            "requested_at",
            "approved_at",
            "scheduled_for",
            "started_at",
            "completed_at",
            "detected_at",
            "resolved_at",
        ]
        base = []
        if hasattr(super(), "get_readonly_fields"):
            base = list(super().get_readonly_fields(request, obj))
        return tuple(sorted(set(base + _available(self.model, candidates))))

    def get_date_hierarchy(self, request):
        for name in [
            "created_at",
            "requested_at",
            "approved_at",
            "scheduled_for",
            "started_at",
            "completed_at",
            "detected_at",
            "resolved_at",
        ]:
            if _has_field(self.model, name):
                return name
        return None


@admin.register(RetentionPolicy)
class RetentionPolicyAdmin(ReadonlyTimestampsMixin, admin.ModelAdmin):
    list_display = tuple(
        _available(RetentionPolicy, ["name", "days", "is_active", "user", "category", "created_at"])
    )
    list_filter = tuple(_available(RetentionPolicy, ["is_active"]))
    search_fields = tuple(_available(RetentionPolicy, ["name"]))


@admin.register(DeletionRequest)
class DeletionRequestAdmin(ReadonlyTimestampsMixin, admin.ModelAdmin):
    list_select_related = True

    list_display = tuple(
        _available(
            DeletionRequest,
            [
                "id",
                "user",
                "target",
                "document",
                "category",
                "status",
                "requested_at",
                "scheduled_for",
                "completed_at",
            ],
        )
    )
    list_filter = ("status", "target")
    search_fields = ("id", "user__username", "user__email", "document__title")


@admin.register(PurgeJob)
class PurgeJobAdmin(ReadonlyTimestampsMixin, admin.ModelAdmin):
    list_display = tuple(
        _available(
            PurgeJob,
            [
                "id",
                "status",
                "items_total",
                "items_succeeded",
                "items_failed",
                "started_at",
                "finished_at",
            ],
        )
    )
    list_filter = ("status",)
    search_fields = ("id",)


@admin.register(ExposureIncident)
class ExposureIncidentAdmin(ReadonlyTimestampsMixin, admin.ModelAdmin):
    list_display = tuple(
        _available(
            ExposureIncident,
            [
                "id",
                "severity",
                "reporter",
                "impacted_user",
                "detected_at",
                "resolved_at",
                "created_at",
            ],
        )
    )
    list_filter = ("severity",)
    search_fields = ("id", "reporter__username", "impacted_user__username")


@admin.register(DataExportRequest)
class DataExportRequestAdmin(ReadonlyTimestampsMixin, admin.ModelAdmin):
    list_select_related = True
    list_display = tuple(
        _available(
            DataExportRequest,
            ["id", "user", "status", "requested_at", "fulfilled_at", "expires_at"],
        )
    )
    list_filter = ("status",)
    search_fields = ("id", "user__username", "user__email")
