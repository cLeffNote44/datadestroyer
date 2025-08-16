from django.contrib import admin

from .models import Message, MessageThread, ThreadParticipant


def _has_field(model, name: str) -> bool:
    try:
        model._meta.get_field(name)
        return True
    except Exception:
        return False


class ThreadParticipantInline(admin.TabularInline):
    model = ThreadParticipant
    extra = 0

    def get_fields(self, request, obj=None):
        base = ["user", "joined_at", "last_read_at"]
        # Include optional "role" field if it exists
        if _has_field(ThreadParticipant, "role"):
            base.insert(1, "role")
        return [f for f in base if _has_field(ThreadParticipant, f)]

    def get_readonly_fields(self, request, obj=None):
        return tuple([f for f in ["joined_at", "last_read_at"] if _has_field(ThreadParticipant, f)])


@admin.register(MessageThread)
class MessageThreadAdmin(admin.ModelAdmin):
    inlines = [ThreadParticipantInline]

    def participants_list(self, obj):
        accessor = ThreadParticipant._meta.get_field("thread").remote_field.get_accessor_name()
        qs = getattr(obj, accessor).select_related("user")
        try:
            usernames = qs.values_list("user__username", flat=True)
            return ", ".join(sorted(set(usernames)))
        except Exception:
            return ", ".join([str(tp) for tp in qs.all()])

    participants_list.short_description = "Participants"

    def get_list_display(self, request):
        fields = ["subject", "participants_list"]
        if _has_field(self.model, "created_at"):
            fields.append("created_at")
        return tuple(fields)

    def get_date_hierarchy(self, request):
        return "created_at" if _has_field(self.model, "created_at") else None

    def get_search_fields(self, request):
        return ("subject",)

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        try:
            matching_threads = ThreadParticipant.objects.filter(
                user__username__icontains=search_term
            ).values_list("thread_id", flat=True)
            queryset |= self.model.objects.filter(pk__in=list(matching_threads))
            use_distinct = True
        except Exception:
            pass
        return queryset, use_distinct


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_select_related = True

    def get_list_display(self, request):
        preferred = ["thread", "sender", "recipient", "status", "created_at"]
        return tuple([f for f in preferred if _has_field(self.model, f) or f in ("thread",)])

    def get_list_filter(self, request):
        return tuple([f for f in ["status", "is_encrypted"] if _has_field(self.model, f)])

    def get_search_fields(self, request):
        fields = ["thread__subject"]
        if _has_field(self.model, "sender"):
            fields.append("sender__username")
        if _has_field(self.model, "recipient"):
            fields.append("recipient__username")
        return tuple(fields)

    def get_readonly_fields(self, request, obj=None):
        candidates = ["deletion_date", "read_at", "delivered_at"]
        return tuple([f for f in candidates if _has_field(self.model, f)])

    def get_date_hierarchy(self, request):
        return "created_at" if _has_field(self.model, "created_at") else None


@admin.register(ThreadParticipant)
class ThreadParticipantAdmin(admin.ModelAdmin):
    list_select_related = True

    def get_list_display(self, request):
        fields = ["thread", "user"]
        if _has_field(self.model, "role"):
            fields.append("role")
        if _has_field(self.model, "joined_at"):
            fields.append("joined_at")
        if _has_field(self.model, "last_read_at"):
            fields.append("last_read_at")
        return tuple(fields)

    def get_search_fields(self, request):
        fields = []
        if _has_field(self.model, "user"):
            fields += ["user__username", "user__email"]
        if _has_field(self.model, "thread"):
            fields += ["thread__subject"]
        return tuple(fields)
