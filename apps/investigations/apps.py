from django.apps import AppConfig


class InvestigationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.investigations"
    verbose_name = "Investigations"

    def ready(self):
        """Import signal handlers when the app is ready"""
        try:
            __import__("apps.investigations.signals")
        except ImportError:
            pass
