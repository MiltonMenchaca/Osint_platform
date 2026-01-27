from django.apps import AppConfig


class EntitiesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.entities"
    verbose_name = "Entities"

    def ready(self):
        """Import signal handlers when the app is ready"""
        try:
            __import__("apps.entities.signals")
        except ImportError:
            pass
