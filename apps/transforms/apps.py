from django.apps import AppConfig


class TransformsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.transforms"
    verbose_name = "Transforms"

    def ready(self):
        """Import signal handlers when the app is ready"""
        try:
            import apps.transforms.signals  # noqa F401
        except ImportError:
            pass
