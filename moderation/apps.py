from django.apps import AppConfig


class ModerationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "moderation"

    def ready(self):
        # Import signal handlers to register them
        pass
