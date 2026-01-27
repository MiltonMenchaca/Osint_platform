"""Celery configuration for OSINT platform"""

import os
import time
import traceback

from celery import Celery, Task
from celery.utils.log import get_task_logger
from django.core.cache import cache

from .redis import get_celery_config

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.development")

# Create Celery app
app = Celery("osint")

# Load configuration from Django settings
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load Celery configuration
celery_config = get_celery_config()
app.conf.update(celery_config)

# Auto-discover tasks from all registered Django apps
app.autodiscover_tasks()

# Task routing configuration
app.conf.task_routes = {
    # Transform execution tasks
    "apps.transforms.tasks.execute_transform": {"queue": "transforms"},
    "apps.transforms.tasks.execute_transform_batch": {"queue": "transforms"},
    "apps.transforms.tasks.cleanup_transform_results": {"queue": "cleanup"},
    # Investigation tasks
    "apps.investigations.tasks.generate_investigation_report": {"queue": "reports"},
    "apps.investigations.tasks.export_investigation_data": {"queue": "exports"},
    "apps.investigations.tasks.cleanup_old_investigations": {"queue": "cleanup"},
    # Entity processing tasks
    "apps.entities.tasks.process_entity_batch": {"queue": "entities"},
    "apps.entities.tasks.merge_duplicate_entities": {"queue": "entities"},
    "apps.entities.tasks.update_entity_relationships": {"queue": "entities"},
    # Notification tasks
    "apps.authentication.tasks.send_notification_email": {"queue": "notifications"},
    "apps.authentication.tasks.cleanup_expired_tokens": {"queue": "cleanup"},
    # System maintenance tasks
    "core.tasks.system_health_check": {"queue": "system"},
    "core.tasks.cleanup_temp_files": {"queue": "cleanup"},
    "core.tasks.generate_system_report": {"queue": "reports"},
}

# Queue configuration
app.conf.task_default_queue = "default"
app.conf.task_queues = {
    "default": {
        "exchange": "default",
        "exchange_type": "direct",
        "routing_key": "default",
    },
    "transforms": {
        "exchange": "transforms",
        "exchange_type": "direct",
        "routing_key": "transforms",
    },
    "entities": {
        "exchange": "entities",
        "exchange_type": "direct",
        "routing_key": "entities",
    },
    "reports": {
        "exchange": "reports",
        "exchange_type": "direct",
        "routing_key": "reports",
    },
    "exports": {
        "exchange": "exports",
        "exchange_type": "direct",
        "routing_key": "exports",
    },
    "notifications": {
        "exchange": "notifications",
        "exchange_type": "direct",
        "routing_key": "notifications",
    },
    "cleanup": {
        "exchange": "cleanup",
        "exchange_type": "direct",
        "routing_key": "cleanup",
    },
    "system": {
        "exchange": "system",
        "exchange_type": "direct",
        "routing_key": "system",
    },
}

# Task priority configuration
app.conf.task_default_priority = 5
app.conf.worker_disable_rate_limits = False
app.conf.task_inherit_parent_priority = True

# Task retry configuration
app.conf.task_default_retry_delay = 60  # 1 minute
app.conf.task_max_retries = 3

# Worker configuration
app.conf.worker_log_format = "[%(asctime)s: %(levelname)s/%(processName)s] %(message)s"
app.conf.worker_task_log_format = "[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s"

# Beat schedule for periodic tasks
app.conf.beat_schedule = {
    # System maintenance tasks
    "system-health-check": {
        "task": "core.tasks.system_health_check",
        "schedule": 300.0,  # Every 5 minutes
        "options": {"queue": "system", "priority": 8},
    },
    "cleanup-temp-files": {
        "task": "core.tasks.cleanup_temp_files",
        "schedule": 3600.0,  # Every hour
        "options": {"queue": "cleanup", "priority": 3},
    },
    "cleanup-old-transform-results": {
        "task": "apps.transforms.tasks.cleanup_transform_results",
        "schedule": 7200.0,  # Every 2 hours
        "options": {"queue": "cleanup", "priority": 3},
    },
    "cleanup-expired-tokens": {
        "task": "apps.authentication.tasks.cleanup_expired_tokens",
        "schedule": 86400.0,  # Daily
        "options": {"queue": "cleanup", "priority": 2},
    },
    "cleanup-old-investigations": {
        "task": "apps.investigations.tasks.cleanup_old_investigations",
        "schedule": 86400.0,  # Daily
        "options": {"queue": "cleanup", "priority": 2},
    },
    # Entity processing tasks
    "merge-duplicate-entities": {
        "task": "apps.entities.tasks.merge_duplicate_entities",
        "schedule": 21600.0,  # Every 6 hours
        "options": {"queue": "entities", "priority": 4},
    },
    "update-entity-relationships": {
        "task": "apps.entities.tasks.update_entity_relationships",
        "schedule": 43200.0,  # Every 12 hours
        "options": {"queue": "entities", "priority": 4},
    },
    # Reporting tasks
    "generate-daily-system-report": {
        "task": "core.tasks.generate_system_report",
        "schedule": 86400.0,  # Daily
        "options": {"queue": "reports", "priority": 2},
    },
}

# Error handling configuration
app.conf.task_reject_on_worker_lost = True
app.conf.task_acks_late = True

# Security configuration
app.conf.worker_hijack_root_logger = False
app.conf.worker_log_color = False

# Monitoring configuration
app.conf.worker_send_task_events = True
app.conf.task_send_sent_event = True


class OSINTTask(Task):
    """Base task class for OSINT platform"""

    def __init__(self):
        self.logger = get_task_logger(self.__class__.__name__)

    def on_success(self, retval, task_id, args, kwargs):
        """Called when task succeeds"""
        self.logger.info(f"Task {task_id} completed successfully")

        # Update task statistics
        cache_key = f"task_stats:{self.name}:success"
        cache.set(cache_key, cache.get(cache_key, 0) + 1, 86400)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails"""
        self.logger.error(
            f"Task {task_id} failed: {exc}",
            extra={
                "task_id": task_id,
                "task_name": self.name,
                "args": args,
                "kwargs": kwargs,
                "exception": str(exc),
                "traceback": traceback.format_exc(),
            },
        )

        # Update task statistics
        cache_key = f"task_stats:{self.name}:failure"
        cache.set(cache_key, cache.get(cache_key, 0) + 1, 86400)

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called when task is retried"""
        self.logger.warning(
            f"Task {task_id} retrying: {exc}",
            extra={
                "task_id": task_id,
                "task_name": self.name,
                "retry_count": self.request.retries,
                "max_retries": self.max_retries,
                "exception": str(exc),
            },
        )

        # Update task statistics
        cache_key = f"task_stats:{self.name}:retry"
        cache.set(cache_key, cache.get(cache_key, 0) + 1, 86400)

    def apply_async(self, args=None, kwargs=None, **options):
        """Override apply_async to add custom logic"""

        # Add task metadata
        if "headers" not in options:
            options["headers"] = {}

        options["headers"].update(
            {
                "submitted_at": time.time(),
                "task_version": getattr(self, "version", "1.0"),
            }
        )

        # Log task submission
        self.logger.info(
            f"Submitting task {self.name}",
            extra={
                "task_name": self.name,
                "args": args,
                "kwargs": kwargs,
                "options": options,
            },
        )

        return super().apply_async(args, kwargs, **options)


# Set custom task base class
app.Task = OSINTTask


# Task monitoring functions
def get_task_stats(task_name: str = None):
    """Get task execution statistics"""
    if task_name:
        return {
            "success": cache.get(f"task_stats:{task_name}:success", 0),
            "failure": cache.get(f"task_stats:{task_name}:failure", 0),
            "retry": cache.get(f"task_stats:{task_name}:retry", 0),
        }
    else:
        # Get stats for all tasks
        stats = {}
        for route in app.conf.task_routes.keys():
            stats[route] = get_task_stats(route)
        return stats


def get_queue_stats():
    """Get queue statistics"""
    try:
        inspect = app.control.inspect()
        active = inspect.active()
        scheduled = inspect.scheduled()
        reserved = inspect.reserved()

        return {
            "active": active,
            "scheduled": scheduled,
            "reserved": reserved,
        }
    except Exception as e:
        return {"error": str(e)}


def get_worker_stats():
    """Get worker statistics"""
    try:
        inspect = app.control.inspect()
        stats = inspect.stats()
        return stats
    except Exception as e:
        return {"error": str(e)}


# Health check function
def celery_health_check():
    """Check Celery health"""
    try:
        # Check if workers are available
        inspect = app.control.inspect()
        stats = inspect.stats()

        if not stats:
            return {"status": "unhealthy", "reason": "No workers available"}

        # Check broker connection
        app.broker_connection().ensure_connection(max_retries=3)

        # Check result backend
        if app.conf.result_backend:
            app.backend.get("test")

        return {
            "status": "healthy",
            "workers": len(stats),
            "queues": list(app.conf.task_queues.keys()),
        }

    except Exception as e:
        return {"status": "unhealthy", "reason": str(e)}


# Debug task for testing
@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup"""
    print(f"Request: {self.request!r}")
    return "Debug task completed successfully"
