"""Database configuration for OSINT platform"""

import os
from typing import Any, Dict

# Base database configuration
BASE_DATABASE_CONFIG = {
    "ENGINE": "django.db.backends.postgresql",
    "OPTIONS": {
        "connect_timeout": 10,
        "options": "-c default_transaction_isolation=read_committed",
    },
    "CONN_MAX_AGE": 600,  # 10 minutes
    "ATOMIC_REQUESTS": True,
}

# Development database configuration
DEVELOPMENT_DATABASE_CONFIG = {
    **BASE_DATABASE_CONFIG,
    "NAME": os.getenv("DB_NAME", "osint_dev"),
    "USER": os.getenv("DB_USER", "osint_user"),
    "PASSWORD": os.getenv("DB_PASSWORD", "osint_password"),
    "HOST": os.getenv("DB_HOST", "localhost"),
    "PORT": os.getenv("DB_PORT", "5432"),
    "OPTIONS": {
        **BASE_DATABASE_CONFIG["OPTIONS"],
        "sslmode": "prefer",
    },
}

# Production database configuration
PRODUCTION_DATABASE_CONFIG = {
    **BASE_DATABASE_CONFIG,
    "NAME": os.getenv("DB_NAME"),
    "USER": os.getenv("DB_USER"),
    "PASSWORD": os.getenv("DB_PASSWORD"),
    "HOST": os.getenv("DB_HOST"),
    "PORT": os.getenv("DB_PORT", "5432"),
    "OPTIONS": {
        **BASE_DATABASE_CONFIG["OPTIONS"],
        "sslmode": "require",
        "sslcert": os.getenv("DB_SSL_CERT"),
        "sslkey": os.getenv("DB_SSL_KEY"),
        "sslrootcert": os.getenv("DB_SSL_ROOT_CERT"),
    },
    "CONN_MAX_AGE": 300,  # 5 minutes in production
}

# Test database configuration
TEST_DATABASE_CONFIG = {
    **BASE_DATABASE_CONFIG,
    "NAME": os.getenv("TEST_DB_NAME", "osint_test"),
    "USER": os.getenv("TEST_DB_USER", "osint_test_user"),
    "PASSWORD": os.getenv("TEST_DB_PASSWORD", "osint_test_password"),
    "HOST": os.getenv("TEST_DB_HOST", "localhost"),
    "PORT": os.getenv("TEST_DB_PORT", "5432"),
    "OPTIONS": {
        "connect_timeout": 5,
    },
    "CONN_MAX_AGE": 0,  # No connection pooling for tests
    "ATOMIC_REQUESTS": False,  # Let tests control transactions
}


# Database routing configuration
class DatabaseRouter:
    """Database router for OSINT platform"""

    def db_for_read(self, model, **hints):
        """Suggest the database to read from"""
        # Use read replica if available
        if os.getenv("READ_DB_HOST"):
            return "read_replica"
        return "default"

    def db_for_write(self, model, **hints):
        """Suggest the database to write to"""
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        """Allow relations if models are in the same app"""
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Ensure that certain apps' models get created on the right database"""
        return True


# Read replica configuration (optional)
READ_REPLICA_CONFIG = {
    **BASE_DATABASE_CONFIG,
    "NAME": os.getenv("READ_DB_NAME", os.getenv("DB_NAME")),
    "USER": os.getenv("READ_DB_USER", os.getenv("DB_USER")),
    "PASSWORD": os.getenv("READ_DB_PASSWORD", os.getenv("DB_PASSWORD")),
    "HOST": os.getenv("READ_DB_HOST"),
    "PORT": os.getenv("READ_DB_PORT", "5432"),
    "OPTIONS": {
        **BASE_DATABASE_CONFIG["OPTIONS"],
        "sslmode": "require" if os.getenv("ENVIRONMENT") == "production" else "prefer",
    },
}


# Database configuration factory
def get_database_config(environment: str = None) -> Dict[str, Any]:
    """Get database configuration for specified environment"""

    if environment is None:
        environment = os.getenv("ENVIRONMENT", "development")

    config = {"default": DEVELOPMENT_DATABASE_CONFIG}

    if environment == "production":
        config["default"] = PRODUCTION_DATABASE_CONFIG
    elif environment == "test":
        config["default"] = TEST_DATABASE_CONFIG

    # Add read replica if configured
    if os.getenv("READ_DB_HOST"):
        config["read_replica"] = READ_REPLICA_CONFIG

    return config


# Connection pool settings
DATABASE_POOL_SETTINGS = {
    "CONN_MAX_AGE": 600,
    "CONN_HEALTH_CHECKS": True,
    "OPTIONS": {
        "MAX_CONNS": 20,
        "MIN_CONNS": 5,
    },
}

# Database backup configuration
BACKUP_CONFIG = {
    "BACKUP_DIR": os.getenv("BACKUP_DIR", "/var/backups/osint"),
    "RETENTION_DAYS": int(os.getenv("BACKUP_RETENTION_DAYS", "30")),
    "COMPRESS": True,
    "ENCRYPT": os.getenv("BACKUP_ENCRYPT", "false").lower() == "true",
    "ENCRYPTION_KEY": os.getenv("BACKUP_ENCRYPTION_KEY"),
}

# Database monitoring configuration
MONITORING_CONFIG = {
    "SLOW_QUERY_THRESHOLD": float(os.getenv("SLOW_QUERY_THRESHOLD", "1.0")),
    "LOG_QUERIES": os.getenv("LOG_QUERIES", "false").lower() == "true",
    "QUERY_CACHE_SIZE": int(os.getenv("QUERY_CACHE_SIZE", "1000")),
}

# Database migration settings
MIGRATION_CONFIG = {
    "MIGRATION_MODULES": {
        "investigations": "apps.investigations.migrations",
        "entities": "apps.entities.migrations",
        "transforms": "apps.transforms.migrations",
        "authentication": "apps.authentication.migrations",
    },
    "MIGRATION_LOCK_TIMEOUT": int(os.getenv("MIGRATION_LOCK_TIMEOUT", "300")),
}
