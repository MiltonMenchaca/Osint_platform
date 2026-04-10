"""Logging configuration for OSINT platform"""

import logging
import logging.config
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


class OSINTFormatter(logging.Formatter):
    """Custom formatter for OSINT platform logs"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_time = datetime.now()

    def format(self, record):
        # Add custom fields
        record.uptime = str(datetime.now() - self.start_time)

        # Add user context if available
        if hasattr(record, "user_id"):
            record.user_context = f"[User:{record.user_id}]"
        else:
            record.user_context = "[System]"

        # Add investigation context if available
        if hasattr(record, "investigation_id"):
            record.investigation_context = f"[Investigation:{record.investigation_id}]"
        else:
            record.investigation_context = ""

        # Add transform context if available
        if hasattr(record, "transform_name"):
            record.transform_context = f"[Transform:{record.transform_name}]"
        else:
            record.transform_context = ""

        return super().format(record)


class SecurityFilter(logging.Filter):
    """Filter to prevent logging of sensitive information"""

    SENSITIVE_PATTERNS = [
        "password",
        "token",
        "api_key",
        "secret",
        "authorization",
        "cookie",
        "session",
    ]

    def filter(self, record):
        # Check message for sensitive information
        message = record.getMessage().lower()

        for pattern in self.SENSITIVE_PATTERNS:
            if pattern in message:
                # Replace sensitive data with placeholder
                record.msg = record.msg.replace(record.args[0] if record.args else "", "[REDACTED]")
                break

        return True


class PerformanceFilter(logging.Filter):
    """Filter to add performance metrics to logs"""

    def filter(self, record):
        # Add memory usage if available
        try:
            import psutil

            process = psutil.Process()
            record.memory_mb = round(process.memory_info().rss / 1024 / 1024, 2)
            record.cpu_percent = process.cpu_percent()
        except ImportError:
            record.memory_mb = 0
            record.cpu_percent = 0

        return True


def get_log_directory() -> Path:
    """Get or create log directory"""
    log_dir = Path(os.getenv("LOG_DIR", "logs"))
    log_dir.mkdir(exist_ok=True)
    return log_dir


def get_logging_config(debug: bool = False) -> Dict[str, Any]:
    """Get logging configuration dictionary"""

    log_dir = get_log_directory()
    log_level = "DEBUG" if debug else "INFO"

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "detailed": {
                "()": OSINTFormatter,
                "format": (
                    "{asctime} | {levelname:8} | {name:20} | "
                    "{user_context} {investigation_context} {transform_context} | "
                    "{funcName}:{lineno} | {message} | "
                    "Memory: {memory_mb}MB CPU: {cpu_percent}%"
                ),
                "style": "{",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "simple": {
                "format": "{asctime} | {levelname} | {name} | {message}",
                "style": "{",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": (
                    "asctime levelname name funcName lineno message "
                    "user_id investigation_id transform_name memory_mb cpu_percent"
                ),
            },
        },
        "filters": {
            "security": {"()": SecurityFilter},
            "performance": {"()": PerformanceFilter},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "simple",
                "filters": ["security"],
                "stream": "ext://sys.stdout",
            },
            "file_detailed": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "detailed",
                "filters": ["security", "performance"],
                "filename": str(log_dir / "osint_detailed.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf-8",
            },
            "file_error": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "detailed",
                "filters": ["security"],
                "filename": str(log_dir / "osint_errors.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 10,
                "encoding": "utf-8",
            },
            "file_security": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "WARNING",
                "formatter": "detailed",
                "filename": str(log_dir / "osint_security.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 10,
                "encoding": "utf-8",
            },
            "file_performance": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "json",
                "filters": ["performance"],
                "filename": str(log_dir / "osint_performance.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf-8",
            },
            "file_transforms": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "detailed",
                "filters": ["security"],
                "filename": str(log_dir / "osint_transforms.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf-8",
            },
        },
        "loggers": {
            "django": {
                "handlers": ["console", "file_detailed"],
                "level": "INFO",
                "propagate": False,
            },
            "django.request": {
                "handlers": ["file_error", "console"],
                "level": "ERROR",
                "propagate": False,
            },
            "django.security": {
                "handlers": ["file_security", "console"],
                "level": "WARNING",
                "propagate": False,
            },
            "celery": {
                "handlers": ["console", "file_detailed"],
                "level": "INFO",
                "propagate": False,
            },
            "celery.task": {
                "handlers": ["file_transforms", "console"],
                "level": "INFO",
                "propagate": False,
            },
            "apps.transforms": {
                "handlers": ["file_transforms", "console"],
                "level": "DEBUG" if debug else "INFO",
                "propagate": False,
            },
            "apps.investigations": {
                "handlers": ["console", "file_detailed"],
                "level": "DEBUG" if debug else "INFO",
                "propagate": False,
            },
            "apps.entities": {
                "handlers": ["console", "file_detailed"],
                "level": "DEBUG" if debug else "INFO",
                "propagate": False,
            },
            "apps.authentication": {
                "handlers": ["file_security", "console"],
                "level": "INFO",
                "propagate": False,
            },
            "performance": {
                "handlers": ["file_performance"],
                "level": "INFO",
                "propagate": False,
            },
        },
        "root": {"level": log_level, "handlers": ["console", "file_detailed"]},
    }

    return config


def setup_logging(debug: bool = False):
    """Setup logging configuration"""
    config = get_logging_config(debug)
    logging.config.dictConfig(config)

    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info("OSINT Platform logging system initialized")
    logger.info(f"Log directory: {get_log_directory()}")
    logger.info(f"Debug mode: {debug}")


class OSINTLoggerAdapter(logging.LoggerAdapter):
    """Custom logger adapter for OSINT platform"""

    def __init__(self, logger, extra=None):
        super().__init__(logger, extra or {})

    def process(self, msg, kwargs):
        # Add extra context to log record
        if "extra" not in kwargs:
            kwargs["extra"] = {}

        kwargs["extra"].update(self.extra)
        return msg, kwargs

    def log_transform_start(self, transform_name: str, input_data: dict, user_id: int = None):
        """Log transform execution start"""
        extra = {
            "transform_name": transform_name,
            "user_id": user_id,
            "event_type": "transform_start",
        }
        self.info(f"Starting transform execution: {transform_name}", extra=extra)

    def log_transform_end(
        self,
        transform_name: str,
        execution_time: float,
        result_count: int,
        user_id: int = None,
    ):
        """Log transform execution end"""
        extra = {
            "transform_name": transform_name,
            "user_id": user_id,
            "execution_time": execution_time,
            "result_count": result_count,
            "event_type": "transform_end",
        }
        self.info(
            f"Transform execution completed: {transform_name} "
            f"(Time: {execution_time:.2f}s, Results: {result_count})",
            extra=extra,
        )

    def log_transform_error(self, transform_name: str, error: Exception, user_id: int = None):
        """Log transform execution error"""
        extra = {
            "transform_name": transform_name,
            "user_id": user_id,
            "error_type": type(error).__name__,
            "event_type": "transform_error",
        }
        self.error(
            f"Transform execution failed: {transform_name} - {str(error)}",
            extra=extra,
            exc_info=True,
        )

    def log_security_event(
        self,
        event_type: str,
        user_id: int = None,
        ip_address: str = None,
        details: dict = None,
    ):
        """Log security-related events"""
        extra = {
            "user_id": user_id,
            "ip_address": ip_address,
            "event_type": f"security_{event_type}",
            "security_event": True,
        }

        if details:
            extra.update(details)

        message = f"Security event: {event_type}"
        if user_id:
            message += f" (User: {user_id})"
        if ip_address:
            message += f" (IP: {ip_address})"

        self.warning(message, extra=extra)

    def log_performance_metric(self, metric_name: str, value: float, unit: str = "", context: dict = None):
        """Log performance metrics"""
        extra = {
            "metric_name": metric_name,
            "metric_value": value,
            "metric_unit": unit,
            "event_type": "performance_metric",
        }

        if context:
            extra.update(context)

        # Use performance logger
        perf_logger = logging.getLogger("performance")
        perf_logger.info(f"Performance metric: {metric_name} = {value} {unit}", extra=extra)


def get_logger(name: str, **context) -> OSINTLoggerAdapter:
    """Get a configured logger with optional context"""
    logger = logging.getLogger(name)
    return OSINTLoggerAdapter(logger, context)


# Convenience functions for common logging scenarios
def log_api_request(logger, request, response_time: float = None):
    """Log API request details"""
    extra = {
        "method": request.method,
        "path": request.path,
        "user_id": getattr(request.user, "id", None) if hasattr(request, "user") else None,
        "ip_address": get_client_ip(request),
        "event_type": "api_request",
    }

    if response_time:
        extra["response_time"] = response_time

    message = f"{request.method} {request.path}"
    if response_time:
        message += f" ({response_time:.3f}s)"

    logger.info(message, extra=extra)


def log_database_query(logger, query: str, execution_time: float, result_count: int = None):
    """Log database query performance"""
    extra = {
        "query_type": query.split()[0].upper() if query else "UNKNOWN",
        "execution_time": execution_time,
        "event_type": "database_query",
    }

    if result_count is not None:
        extra["result_count"] = result_count

    # Use performance logger for database queries
    perf_logger = logging.getLogger("performance")
    perf_logger.info(f"Database query executed ({execution_time:.3f}s)", extra=extra)


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


# Error tracking utilities
class ErrorTracker:
    """Track and aggregate errors for monitoring"""

    def __init__(self):
        self.logger = get_logger("error_tracker")
        self.error_counts = {}

    def track_error(self, error: Exception, context: dict = None):
        """Track an error occurrence"""
        error_type = type(error).__name__
        error_key = f"{error_type}:{str(error)[:100]}"

        # Increment error count
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1

        # Log error with context
        extra = {
            "error_type": error_type,
            "error_count": self.error_counts[error_key],
            "event_type": "error_tracked",
        }

        if context:
            extra.update(context)

        self.logger.error(
            f"Error tracked: {error_type} (Count: {self.error_counts[error_key]})",
            extra=extra,
            exc_info=True,
        )

    def get_error_summary(self) -> dict:
        """Get summary of tracked errors"""
        return dict(self.error_counts)


# Global error tracker instance
error_tracker = ErrorTracker()
