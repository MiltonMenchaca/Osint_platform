import copy
import logging
import os

from . import base as base_settings

BASE_DIR = base_settings.BASE_DIR
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY must be set via environment in production")

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
SIMPLE_JWT = copy.deepcopy(base_settings.SIMPLE_JWT)
SIMPLE_JWT["SIGNING_KEY"] = SECRET_KEY

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

DEBUG = os.environ.get("DEBUG", "False") == "True"

ALLOWED_HOSTS = [
    os.environ.get("ALLOWED_HOST", "osint-platform.com"),
    f"api.{os.environ.get('ALLOWED_HOST', 'osint-platform.com')}",
]

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "osint_platform"),
        "USER": os.environ.get("DB_USER", "osint_user"),
        "PASSWORD": os.environ.get("DB_PASSWORD"),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
        "CONN_MAX_AGE": 600,
    }
}

# Redis Configuration for Production
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = os.environ.get("REDIS_PORT", "6379")
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "")

if REDIS_PASSWORD:
    REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}"
else:
    REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}"

# Celery Configuration for Production
CELERY_BROKER_URL = f"{REDIS_URL}/0"
CELERY_RESULT_BACKEND = f"{REDIS_URL}/0"
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_CONNECTION_MAX_RETRIES = 10
CELERY_WORKER_CONCURRENCY = int(os.environ.get("CELERY_WORKERS", "8"))

# Cache Configuration
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"{REDIS_URL}/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 50,
                "retry_on_timeout": True,
            },
        },
        "KEY_PREFIX": "osint_cache_prod",
        "TIMEOUT": 300,
    }
}

# Email Configuration for Production
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL",
    "noreply@osint-platform.com",
)

# Security Settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "31536000"))
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "True") == "True"
SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "True") == "True"
CSRF_COOKIE_SECURE = os.environ.get("CSRF_COOKIE_SECURE", "True") == "True"
X_FRAME_OPTIONS = "DENY"

# CORS Settings for Production
CORS_ALLOWED_ORIGINS = [
    origin.strip() for origin in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",") if origin.strip()
]
if not CORS_ALLOWED_ORIGINS:
    CORS_ALLOWED_ORIGINS = [
        f"https://{os.environ.get('FRONTEND_HOST', 'osint-platform.com')}",
        f"https://www.{os.environ.get('FRONTEND_HOST', 'osint-platform.com')}",
    ]

CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if origin.strip()
]
if not CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS = [
        f"https://{os.environ.get('FRONTEND_HOST', 'osint-platform.com')}",
        f"https://www.{os.environ.get('FRONTEND_HOST', 'osint-platform.com')}",
    ]

CORS_ALLOW_CREDENTIALS = True

# Static files configuration for production
STATIC_ROOT = "/var/www/osint_platform/static/"
MEDIA_ROOT = "/var/www/osint_platform/media/"

# Production logging
LOGGING["handlers"]["file"]["filename"] = "/var/log/osint_platform/django.log"
LOGGING["handlers"]["celery"]["filename"] = "/var/log/osint_platform/celery.log"

# Sentry Configuration (Error Tracking)
SENTRY_DSN = os.environ.get("SENTRY_DSN")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration

    sentry_logging = LoggingIntegration(
        level=logging.INFO,
        event_level=logging.ERROR,
    )

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            sentry_logging,
        ],
        traces_sample_rate=0.1,
        send_default_pii=True,
        environment=os.environ.get("ENVIRONMENT", "production"),
    )

# Transform execution settings for production
TRANSFORM_TIMEOUT = 1800  # 30 minutes for production
TRANSFORM_MAX_RETRIES = 3

# OSINT Tools Configuration for Production
OSINT_TOOLS = {
    "assetfinder": {
        "command": "/usr/local/bin/assetfinder",
        "timeout": 600,
        "enabled": True,
    },
    "amass": {
        "command": "/usr/local/bin/amass",
        "timeout": 1800,
        "enabled": True,
    },
    "nmap": {
        "command": "/usr/bin/nmap",
        "timeout": 1200,
        "enabled": True,
    },
    "shodan": {
        "api_key": os.environ.get("SHODAN_API_KEY", ""),
        "timeout": 60,
        "enabled": bool(os.environ.get("SHODAN_API_KEY")),
    },
}

# Rate Limiting
RATE_LIMIT_ENABLE = True
RATE_LIMIT_PER_MINUTE = 60
RATE_LIMIT_PER_HOUR = 1000

# Monitoring and Health Checks
HEALTH_CHECK_ENABLED = True
METRICS_ENABLED = True

# Backup Configuration
BACKUP_ENABLED = True
BACKUP_SCHEDULE = "0 2 * * *"  # Daily at 2 AM
BACKUP_RETENTION_DAYS = 30
