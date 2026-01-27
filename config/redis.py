"""Redis configuration for OSINT platform"""

import os
from typing import Any, Dict

# Base Redis configuration
BASE_REDIS_CONFIG = {
    "BACKEND": "django_redis.cache.RedisCache",
    "OPTIONS": {
        "CLIENT_CLASS": "django_redis.client.DefaultClient",
        "CONNECTION_POOL_KWARGS": {
            "max_connections": 50,
            "retry_on_timeout": True,
            "socket_keepalive": True,
            "socket_keepalive_options": {},
        },
        "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
        "IGNORE_EXCEPTIONS": True,
    },
    "TIMEOUT": 300,  # 5 minutes default timeout
    "VERSION": 1,
    "KEY_PREFIX": "osint",
}

# Development Redis configuration
DEVELOPMENT_REDIS_CONFIG = {
    **BASE_REDIS_CONFIG,
    "LOCATION": (
        f"redis://{os.getenv('REDIS_HOST', 'localhost')}:"
        f"{os.getenv('REDIS_PORT', '6379')}/{os.getenv('REDIS_DB', '0')}"
    ),
    "OPTIONS": {
        **BASE_REDIS_CONFIG["OPTIONS"],
        "PASSWORD": os.getenv("REDIS_PASSWORD"),
    },
}

# Production Redis configuration
PRODUCTION_REDIS_CONFIG = {
    **BASE_REDIS_CONFIG,
    "LOCATION": f"redis://{os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT', '6379')}/{os.getenv('REDIS_DB', '0')}",
    "OPTIONS": {
        **BASE_REDIS_CONFIG["OPTIONS"],
        "PASSWORD": os.getenv("REDIS_PASSWORD"),
        "CONNECTION_POOL_KWARGS": {
            **BASE_REDIS_CONFIG["OPTIONS"]["CONNECTION_POOL_KWARGS"],
            "ssl_cert_reqs": "required"
            if os.getenv("REDIS_SSL", "false").lower() == "true"
            else None,
            "ssl_ca_certs": os.getenv("REDIS_SSL_CA_CERTS"),
            "ssl_certfile": os.getenv("REDIS_SSL_CERTFILE"),
            "ssl_keyfile": os.getenv("REDIS_SSL_KEYFILE"),
        },
    },
    "TIMEOUT": 600,  # 10 minutes in production
}

# Test Redis configuration
TEST_REDIS_CONFIG = {
    **BASE_REDIS_CONFIG,
    "LOCATION": (
        f"redis://{os.getenv('TEST_REDIS_HOST', 'localhost')}:"
        f"{os.getenv('TEST_REDIS_PORT', '6379')}/{os.getenv('TEST_REDIS_DB', '1')}"
    ),
    "OPTIONS": {
        **BASE_REDIS_CONFIG["OPTIONS"],
        "PASSWORD": os.getenv("TEST_REDIS_PASSWORD"),
        "CONNECTION_POOL_KWARGS": {
            "max_connections": 10,
            "retry_on_timeout": True,
        },
    },
    "TIMEOUT": 60,  # 1 minute for tests
}


# Cache configuration factory
def get_cache_config(environment: str = None) -> Dict[str, Any]:
    """Get cache configuration for specified environment"""

    if environment is None:
        environment = os.getenv("ENVIRONMENT", "development")

    if environment == "production":
        default_config = PRODUCTION_REDIS_CONFIG
    elif environment == "test":
        default_config = TEST_REDIS_CONFIG
    else:
        default_config = DEVELOPMENT_REDIS_CONFIG

    config = {
        "default": default_config,
        "sessions": {
            **default_config,
            "LOCATION": default_config["LOCATION"].replace(
                f"/{os.getenv('REDIS_DB', '0')}", "/1"
            ),
            "TIMEOUT": 86400,  # 24 hours for sessions
            "KEY_PREFIX": "osint:session",
        },
        "transforms": {
            **default_config,
            "LOCATION": default_config["LOCATION"].replace(
                f"/{os.getenv('REDIS_DB', '0')}", "/2"
            ),
            "TIMEOUT": 3600,  # 1 hour for transform results
            "KEY_PREFIX": "osint:transform",
        },
        "rate_limit": {
            **default_config,
            "LOCATION": default_config["LOCATION"].replace(
                f"/{os.getenv('REDIS_DB', '0')}", "/3"
            ),
            "TIMEOUT": 3600,  # 1 hour for rate limiting
            "KEY_PREFIX": "osint:ratelimit",
        },
    }

    return config


# Celery Redis configuration
CELERY_REDIS_CONFIG = {
    "broker_url": (
        f"redis://:{os.getenv('REDIS_PASSWORD', '')}@"
        f"{os.getenv('REDIS_HOST', 'localhost')}:"
        f"{os.getenv('REDIS_PORT', '6379')}/{os.getenv('CELERY_REDIS_DB', '4')}"
    ),
    "result_backend": (
        f"redis://:{os.getenv('REDIS_PASSWORD', '')}@"
        f"{os.getenv('REDIS_HOST', 'localhost')}:"
        f"{os.getenv('REDIS_PORT', '6379')}/{os.getenv('CELERY_RESULT_DB', '5')}"
    ),
    "broker_connection_retry_on_startup": True,
    "broker_connection_retry": True,
    "broker_connection_max_retries": 10,
    "broker_pool_limit": 10,
    "result_expires": 3600,  # 1 hour
    "result_compression": "gzip",
    "result_serializer": "json",
    "task_serializer": "json",
    "accept_content": ["json"],
    "timezone": "UTC",
    "enable_utc": True,
    "task_track_started": True,
    "task_time_limit": 30 * 60,  # 30 minutes
    "task_soft_time_limit": 25 * 60,  # 25 minutes
    "worker_prefetch_multiplier": 1,
    "worker_max_tasks_per_child": 1000,
    "worker_disable_rate_limits": False,
    "task_acks_late": True,
    "task_reject_on_worker_lost": True,
}


# Celery configuration for different environments
def get_celery_config(environment: str = None) -> Dict[str, Any]:
    """Get Celery configuration for specified environment"""

    if environment is None:
        environment = os.getenv("ENVIRONMENT", "development")

    config = CELERY_REDIS_CONFIG.copy()

    if environment == "production":
        config.update(
            {
                "worker_concurrency": int(os.getenv("CELERY_WORKER_CONCURRENCY", "4")),
                "task_time_limit": 60 * 60,  # 1 hour in production
                "task_soft_time_limit": 55 * 60,  # 55 minutes
                "worker_max_tasks_per_child": 500,
                "broker_transport_options": {
                    "visibility_timeout": 3600,
                    "fanout_prefix": True,
                    "fanout_patterns": True,
                },
            }
        )
    elif environment == "development":
        config.update(
            {
                "worker_concurrency": 2,
                "task_always_eager": os.getenv("CELERY_ALWAYS_EAGER", "false").lower()
                == "true",
                "task_eager_propagates": True,
            }
        )
    elif environment == "test":
        config.update(
            {
                "task_always_eager": True,
                "task_eager_propagates": True,
                "broker_url": f"redis://localhost:6379/{os.getenv('TEST_CELERY_REDIS_DB', '6')}",
                "result_backend": f"redis://localhost:6379/{os.getenv('TEST_CELERY_RESULT_DB', '7')}",
            }
        )

    return config


# Redis monitoring configuration
REDIS_MONITORING_CONFIG = {
    "HEALTH_CHECK_INTERVAL": int(os.getenv("REDIS_HEALTH_CHECK_INTERVAL", "30")),
    "MAX_MEMORY_USAGE": float(os.getenv("REDIS_MAX_MEMORY_USAGE", "0.8")),
    "SLOW_LOG_THRESHOLD": int(
        os.getenv("REDIS_SLOW_LOG_THRESHOLD", "10000")
    ),  # microseconds
    "ALERT_ON_HIGH_MEMORY": os.getenv("REDIS_ALERT_HIGH_MEMORY", "true").lower()
    == "true",
    "ALERT_ON_SLOW_QUERIES": os.getenv("REDIS_ALERT_SLOW_QUERIES", "true").lower()
    == "true",
}

# Redis backup configuration
REDIS_BACKUP_CONFIG = {
    "BACKUP_ENABLED": os.getenv("REDIS_BACKUP_ENABLED", "false").lower() == "true",
    "BACKUP_INTERVAL": int(os.getenv("REDIS_BACKUP_INTERVAL", "3600")),  # seconds
    "BACKUP_DIR": os.getenv("REDIS_BACKUP_DIR", "/var/backups/redis"),
    "RETENTION_DAYS": int(os.getenv("REDIS_BACKUP_RETENTION_DAYS", "7")),
    "COMPRESS": os.getenv("REDIS_BACKUP_COMPRESS", "true").lower() == "true",
}

# Redis cluster configuration (for production scaling)
REDIS_CLUSTER_CONFIG = {
    "ENABLED": os.getenv("REDIS_CLUSTER_ENABLED", "false").lower() == "true",
    "NODES": [
        {
            "host": host.split(":")[0],
            "port": int(host.split(":")[1]) if ":" in host else 6379,
        }
        for host in os.getenv("REDIS_CLUSTER_NODES", "").split(",")
        if host
    ],
    "SKIP_FULL_COVERAGE_CHECK": True,
    "MAX_CONNECTIONS_PER_NODE": 50,
    "READONLY_MODE": False,
}

# Session configuration
SESSION_CONFIG = {
    "SESSION_ENGINE": "django.contrib.sessions.backends.cache",
    "SESSION_CACHE_ALIAS": "sessions",
    "SESSION_COOKIE_AGE": int(os.getenv("SESSION_COOKIE_AGE", "86400")),  # 24 hours
    "SESSION_COOKIE_SECURE": os.getenv("ENVIRONMENT", "development") == "production",
    "SESSION_COOKIE_HTTPONLY": True,
    "SESSION_COOKIE_SAMESITE": "Lax",
    "SESSION_SAVE_EVERY_REQUEST": False,
    "SESSION_EXPIRE_AT_BROWSER_CLOSE": False,
}

# Cache key patterns
CACHE_KEY_PATTERNS = {
    "user_profile": "user:profile:{user_id}",
    "investigation": "investigation:{investigation_id}",
    "transform_result": "transform:result:{execution_id}",
    "entity_graph": "entity:graph:{investigation_id}",
    "api_rate_limit": "ratelimit:{identifier}",
    "tool_status": "tool:status:{tool_name}",
    "search_results": "search:{query_hash}",
}

# Cache timeout settings
CACHE_TIMEOUTS = {
    "user_profile": 3600,  # 1 hour
    "investigation": 1800,  # 30 minutes
    "transform_result": 7200,  # 2 hours
    "entity_graph": 900,  # 15 minutes
    "api_rate_limit": 3600,  # 1 hour
    "tool_status": 300,  # 5 minutes
    "search_results": 1800,  # 30 minutes
}


# Redis connection helper
class RedisConnectionManager:
    """Redis connection manager"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._connection = None

    def get_connection(self):
        """Get Redis connection"""
        if self._connection is None:
            import redis

            self._connection = redis.from_url(
                self.config["LOCATION"],
                **self.config.get("OPTIONS", {}).get("CONNECTION_POOL_KWARGS", {}),
            )
        return self._connection

    def health_check(self) -> bool:
        """Check Redis connection health"""
        try:
            conn = self.get_connection()
            conn.ping()
            return True
        except Exception:
            return False

    def get_info(self) -> Dict[str, Any]:
        """Get Redis server info"""
        try:
            conn = self.get_connection()
            return conn.info()
        except Exception:
            return {}

    def flush_cache(self, pattern: str = None) -> int:
        """Flush cache keys matching pattern"""
        try:
            conn = self.get_connection()
            if pattern:
                keys = conn.keys(pattern)
                if keys:
                    return conn.delete(*keys)
                return 0
            else:
                conn.flushdb()
                return -1  # All keys flushed
        except Exception:
            return 0
