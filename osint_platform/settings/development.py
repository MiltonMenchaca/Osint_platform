import copy
import os

from . import base as base_settings

BASE_DIR = base_settings.BASE_DIR
SECRET_KEY = base_settings.SECRET_KEY

INSTALLED_APPS = list(base_settings.INSTALLED_APPS)
MIDDLEWARE = list(base_settings.MIDDLEWARE)
ROOT_URLCONF = base_settings.ROOT_URLCONF
TEMPLATES = base_settings.TEMPLATES
WSGI_APPLICATION = base_settings.WSGI_APPLICATION
ASGI_APPLICATION = base_settings.ASGI_APPLICATION

AUTH_PASSWORD_VALIDATORS = base_settings.AUTH_PASSWORD_VALIDATORS

LANGUAGE_CODE = base_settings.LANGUAGE_CODE
TIME_ZONE = base_settings.TIME_ZONE
USE_I18N = base_settings.USE_I18N
USE_TZ = base_settings.USE_TZ

STATIC_URL = base_settings.STATIC_URL
STATIC_ROOT = base_settings.STATIC_ROOT
STATICFILES_DIRS = base_settings.STATICFILES_DIRS

MEDIA_URL = base_settings.MEDIA_URL
MEDIA_ROOT = base_settings.MEDIA_ROOT

DEFAULT_AUTO_FIELD = base_settings.DEFAULT_AUTO_FIELD

REST_FRAMEWORK = base_settings.REST_FRAMEWORK
SIMPLE_JWT = base_settings.SIMPLE_JWT

CORS_ALLOW_CREDENTIALS = base_settings.CORS_ALLOW_CREDENTIALS
CORS_ALLOWED_HEADERS = base_settings.CORS_ALLOWED_HEADERS
CORS_ALLOW_METHODS = base_settings.CORS_ALLOW_METHODS

CELERY_TIMEZONE = base_settings.CELERY_TIMEZONE
CELERY_TASK_TRACK_STARTED = base_settings.CELERY_TASK_TRACK_STARTED
CELERY_TASK_TIME_LIMIT = base_settings.CELERY_TASK_TIME_LIMIT
CELERY_TASK_SOFT_TIME_LIMIT = base_settings.CELERY_TASK_SOFT_TIME_LIMIT
CELERY_WORKER_CONCURRENCY = base_settings.CELERY_WORKER_CONCURRENCY
CELERY_WORKER_MAX_TASKS_PER_CHILD = base_settings.CELERY_WORKER_MAX_TASKS_PER_CHILD
CELERY_WORKER_DISABLE_RATE_LIMITS = base_settings.CELERY_WORKER_DISABLE_RATE_LIMITS
CELERY_TASK_SERIALIZER = base_settings.CELERY_TASK_SERIALIZER
CELERY_RESULT_SERIALIZER = base_settings.CELERY_RESULT_SERIALIZER
CELERY_ACCEPT_CONTENT = base_settings.CELERY_ACCEPT_CONTENT
CELERY_RESULT_EXPIRES = base_settings.CELERY_RESULT_EXPIRES
CELERY_TASK_RESULT_EXPIRES = base_settings.CELERY_TASK_RESULT_EXPIRES
CELERY_TASK_ROUTES = base_settings.CELERY_TASK_ROUTES

LOGGING = copy.deepcopy(base_settings.LOGGING)

DEBUG = True

ALLOWED_HOSTS = ["*"]

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases
if os.environ.get("DB_HOST"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DB_NAME", "osint_platform"),
            "USER": os.environ.get("DB_USER", "osint_user"),
            "PASSWORD": os.environ.get("DB_PASSWORD", "osint_password"),
            "HOST": os.environ.get("DB_HOST", "db"),
            "PORT": os.environ.get("DB_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
            "OPTIONS": {
                "timeout": 20,
            },
        }
    }

# Redis Configuration for Development
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")

# Celery Configuration for Development
CELERY_BROKER_URL = f"{REDIS_URL}/0"
CELERY_RESULT_BACKEND = f"{REDIS_URL}/0"
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_CONNECTION_MAX_RETRIES = 10
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Cache Configuration - Using local memory cache for development
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "osint_cache_dev",
        "TIMEOUT": 300,
    }
}

# Email Configuration for Development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
if "PYTEST_CURRENT_TEST" in os.environ:
    EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Development-specific CORS settings
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOWED_ORIGINS = [
    "http://cumulo_admin.local",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]

# Disable HTTPS redirects in development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Development logging
LOGGING["loggers"]["apps"]["level"] = "DEBUG"
LOGGING["handlers"]["console"]["level"] = "DEBUG"

# Django Debug Toolbar (optional)
if DEBUG:
    try:
        __import__("debug_toolbar")

        INSTALLED_APPS.append("debug_toolbar")
        MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
        INTERNAL_IPS = ["127.0.0.1", "localhost"]
    except ImportError:
        pass

# Transform execution settings for development
TRANSFORM_TIMEOUT = 300  # 5 minutes for development
TRANSFORM_MAX_RETRIES = 2

# OSINT Tools Configuration
OSINT_TOOLS = {
    "assetfinder": {
        "command": "assetfinder",
        "timeout": 300,
        "enabled": True,
    },
    "amass": {
        "command": "amass",
        "timeout": 900,
        "enabled": True,
    },
    "nmap": {
        "command": "nmap",
        "timeout": 600,
        "enabled": True,
    },
    "shodan": {
        "api_key": os.environ.get("SHODAN_API_KEY", ""),
        "timeout": 30,
        "enabled": bool(os.environ.get("SHODAN_API_KEY")),
    },
    "holehe": {
        "command": "holehe",
        "timeout": 180,
        "enabled": True,
    },
}
