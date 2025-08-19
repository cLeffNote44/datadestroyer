from django.apps import AppConfig


class DiscoveryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "discovery"
    verbose_name = "Data Discovery & Classification"

    def ready(self):
        """Initialize signals and other app configuration"""
        try:
            from . import signals  # noqa
        except ImportError:
            pass
