from django.contrib import admin

from .models import Document, DocumentAccessLog, DocumentCategory


class DocumentAccessLogInline(admin.TabularInline):
    model = DocumentAccessLog
    extra = 0
    can_delete = False
    show_change_link = False
    readonly_fields = ("user", "action", "success", "ip_address", "accessed_at")
    fields = readonly_fields

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_sensitive", "default_retention_days")
    search_fields = ("name", "slug")
    list_filter = ("is_sensitive",)
    ordering = ("name",)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "owner",
        "category",
        "status",
        "is_encrypted",
        "file_size",
        "created_at",
    )
    list_filter = ("status", "is_encrypted", "category")
    search_fields = ("title", "owner__username", "file_hash")
    readonly_fields = (
        "file_hash",
        "file_size",
        "created_at",
        "updated_at",
        "download_count",
        "last_accessed",
    )
    date_hierarchy = "created_at"
    inlines = [DocumentAccessLogInline]
    list_select_related = ("owner", "category")
    ordering = ("-created_at",)


@admin.register(DocumentAccessLog)
class DocumentAccessLogAdmin(admin.ModelAdmin):
    list_display = ("document", "user", "action", "success", "ip_address", "accessed_at")
    list_filter = ("action", "success")
    search_fields = ("document__title", "user__username", "ip_address")
    date_hierarchy = "accessed_at"
    ordering = ("-accessed_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        if "delete_selected" in actions:
            del actions["delete_selected"]
        return actions
