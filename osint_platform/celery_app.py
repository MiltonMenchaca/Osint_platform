import os

from celery import Celery
from celery.signals import (
    after_task_publish,
    before_task_publish,
    task_failure,
    worker_ready,
    worker_shutdown,
)

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "osint_platform.settings.development",
)

# Create the Celery application
app = Celery("osint_platform")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery configuration
app.conf.update(
    # Task routing
    task_routes={
        "apps.investigations.tasks.execute_transform": {"queue": "transforms"},
        "apps.investigations.tasks.cleanup_old_executions": {"queue": "maintenance"},
        "apps.investigations.tasks.health_check": {"queue": "monitoring"},
    },
    # Task serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Task execution
    task_always_eager=False,
    task_eager_propagates=True,
    task_ignore_result=False,
    task_store_eager_result=True,
    # Task time limits
    task_soft_time_limit=300,  # 5 minutes
    task_time_limit=600,  # 10 minutes
    # Worker configuration
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=False,
    # Result backend configuration
    result_expires=3600,  # 1 hour
    result_persistent=True,
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
    # Security
    worker_hijack_root_logger=False,
    worker_log_color=False,
    # Beat schedule for periodic tasks
    beat_schedule={
        "cleanup-old-executions": {
            "task": "apps.investigations.tasks.cleanup_old_executions",
            "schedule": 3600.0,  # Run every hour
            "options": {"queue": "maintenance"},
        },
        "health-check": {
            "task": "apps.investigations.tasks.health_check",
            "schedule": 300.0,  # Run every 5 minutes
            "options": {"queue": "monitoring"},
        },
        "cleanup-expired-tokens": {
            "task": "apps.authentication.tasks.cleanup_expired_tokens",
            "schedule": 86400.0,  # Run daily
            "options": {"queue": "maintenance"},
        },
        "update-transform-statistics": {
            "task": "apps.transforms.tasks.update_statistics",
            "schedule": 1800.0,  # Run every 30 minutes
            "options": {"queue": "maintenance"},
        },
    },
    beat_schedule_filename="celerybeat-schedule",
)


# Custom task base class
class BaseTask(app.Task):
    """Base task class with common functionality"""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure"""
        import logging

        logger = logging.getLogger(__name__)

        logger.error(
            f"Task {self.name} failed: {exc}",
            extra={
                "task_id": task_id,
                "task_name": self.name,
                "args": args,
                "kwargs": kwargs,
                "exception": str(exc),
                "traceback": str(einfo),
            },
        )

        # Update task execution status if applicable
        if "execution_id" in kwargs:
            try:
                from apps.investigations.models import TransformExecution

                execution = TransformExecution.objects.get(id=kwargs["execution_id"])
                execution.status = "failed"
                execution.error_message = str(exc)
                execution.save()
            except Exception as e:
                logger.error(f"Failed to update execution status: {e}")

    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success"""
        import logging

        logger = logging.getLogger(__name__)

        logger.info(
            f"Task {self.name} completed successfully",
            extra={"task_id": task_id, "task_name": self.name, "result": retval},
        )

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Handle task retry"""
        import logging

        logger = logging.getLogger(__name__)

        logger.warning(
            f"Task {self.name} retrying: {exc}",
            extra={
                "task_id": task_id,
                "task_name": self.name,
                "retry_count": self.request.retries,
                "exception": str(exc),
            },
        )


# Set the base task class
app.Task = BaseTask


# Task discovery
@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery configuration"""
    print(f"Request: {self.request!r}")
    return "Debug task completed"


# Health check task
@app.task(bind=True)
def celery_health_check(self):
    """Health check task for monitoring"""
    import time

    from django.utils import timezone

    start_time = time.time()

    # Simulate some work
    time.sleep(1)

    end_time = time.time()
    execution_time = end_time - start_time

    return {
        "status": "healthy",
        "timestamp": timezone.now().isoformat(),
        "execution_time": execution_time,
        "worker_id": self.request.hostname,
    }


# Task for testing Redis connection
@app.task(bind=True)
def test_redis_connection(self):
    """Test Redis connection"""
    try:
        from django.core.cache import cache

        # Test cache operations
        test_key = "celery_redis_test"
        test_value = "test_value"

        cache.set(test_key, test_value, timeout=60)
        retrieved_value = cache.get(test_key)

        if retrieved_value == test_value:
            cache.delete(test_key)
            return {"status": "success", "message": "Redis connection is working"}
        else:
            return {"status": "error", "message": "Redis cache test failed"}

    except Exception as e:
        return {"status": "error", "message": f"Redis connection failed: {str(e)}"}


@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """Handle worker ready signal"""
    import logging

    logger = logging.getLogger(__name__)
    logger.info(f"Celery worker {sender.hostname} is ready")


@worker_shutdown.connect
def worker_shutdown_handler(sender=None, **kwargs):
    """Handle worker shutdown signal"""
    import logging

    logger = logging.getLogger(__name__)
    logger.info(f"Celery worker {sender.hostname} is shutting down")


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwargs):
    """Handle task failure globally"""
    import logging

    logger = logging.getLogger(__name__)

    logger.error(
        f"Task failure: {sender.name} (ID: {task_id})",
        extra={
            "task_id": task_id,
            "task_name": sender.name,
            "exception": str(exception),
            "traceback": str(traceback),
        },
    )


@before_task_publish.connect
def before_task_publish_handler(sender=None, headers=None, body=None, properties=None, **kwargs):
    """Handle before task publish"""
    import logging

    logger = logging.getLogger(__name__)

    task_name = headers.get("task", "unknown")
    task_id = headers.get("id", "unknown")

    logger.debug(
        f"Publishing task: {task_name} (ID: {task_id})",
        extra={"task_id": task_id, "task_name": task_name, "event": "task_publish"},
    )


@after_task_publish.connect
def after_task_publish_handler(sender=None, headers=None, body=None, **kwargs):
    """Handle after task publish"""
    import logging

    logger = logging.getLogger(__name__)

    task_name = headers.get("task", "unknown")
    task_id = headers.get("id", "unknown")

    logger.debug(
        f"Task published: {task_name} (ID: {task_id})",
        extra={"task_id": task_id, "task_name": task_name, "event": "task_published"},
    )


if __name__ == "__main__":
    app.start()
