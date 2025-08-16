from django.contrib import admin

from .models import ForumCategory, Post, Topic


def _has_field(model, name: str) -> bool:
    try:
        model._meta.get_field(name)
        return True
    except Exception:
        return False


@admin.register(ForumCategory)
class ForumCategoryAdmin(admin.ModelAdmin):
    list_display = (
        ("name", "slug", "created_at")
        if _has_field(ForumCategory, "created_at")
        else ("name", "slug")
    )
    search_fields = ("name", "slug")
    ordering = ("name",)


class PostInline(admin.TabularInline):
    model = Post
    extra = 0
    can_delete = False
    show_change_link = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        fields = ["author", "status"]
        if _has_field(Post, "created_at"):
            fields.append("created_at")
        if _has_field(Post, "updated_at"):
            fields.append("updated_at")
        return tuple(fields)

    def get_fields(self, request, obj=None):
        base = ["author", "status", "created_at"]
        return [f for f in base if _has_field(Post, f)]


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    inlines = [PostInline]
    list_select_related = True

    def get_list_display(self, request):
        preferred = ["title", "author", "category", "status", "created_at"]
        fields = []
        for f in preferred:
            if (
                f == "author"
                and not _has_field(self.model, "author")
                and _has_field(self.model, "user")
            ):
                fields.append("user")
            elif _has_field(self.model, f) or f in ("title", "category"):
                fields.append(f)
        return tuple(fields)

    def get_list_filter(self, request):
        return tuple([f for f in ["status", "category"] if _has_field(self.model, f)])

    def get_search_fields(self, request):
        fields = ["title"]
        if _has_field(self.model, "author"):
            fields.append("author__username")
        elif _has_field(self.model, "user"):
            fields.append("user__username")
        return tuple(fields)

    def get_date_hierarchy(self, request):
        return "created_at" if _has_field(self.model, "created_at") else None


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_select_related = True

    def get_list_display(self, request):
        preferred = ["topic", "author", "status", "created_at"]
        fields = []
        for f in preferred:
            if (
                f == "author"
                and not _has_field(self.model, "author")
                and _has_field(self.model, "user")
            ):
                fields.append("user")
            elif _has_field(self.model, f) or f == "topic":
                fields.append(f)
        return tuple(fields)

    def get_list_filter(self, request):
        return tuple([f for f in ["status"] if _has_field(self.model, f)])

    def get_search_fields(self, request):
        fields = ["topic__title"]
        if _has_field(self.model, "author"):
            fields.append("author__username")
        elif _has_field(self.model, "user"):
            fields.append("user__username")
        return tuple(fields)

    def get_date_hierarchy(self, request):
        return "created_at" if _has_field(self.model, "created_at") else None
