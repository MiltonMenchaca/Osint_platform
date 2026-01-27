import os

import django


def test_django_settings_loaded():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "osint_platform.settings.development")
    django.setup()
    from django.conf import settings

    assert settings.configured
