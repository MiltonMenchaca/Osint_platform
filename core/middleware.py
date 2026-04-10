"""Custom middleware for OSINT platform"""

import json
import logging
import os
import shutil
import time
import uuid
from typing import Dict, Optional

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.deprecation import MiddlewareMixin
from rest_framework.authtoken.models import Token

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(MiddlewareMixin):
    """Middleware for logging HTTP requests and responses"""

    def process_request(self, request: HttpRequest) -> None:
        """Process incoming request"""

        # Generate unique request ID
        request.request_id = str(uuid.uuid4())
        request.start_time = time.time()

        # Log request details
        user_id = (
            getattr(request.user, "id", None)
            if hasattr(request, "user") and request.user.is_authenticated
            else None
        )

        # Get client IP
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")

        # Prepare request data (exclude sensitive information)
        request_data = {}
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                if request.content_type == "application/json":
                    request_data = json.loads(request.body.decode("utf-8"))
                    # Remove sensitive fields
                    sensitive_fields = ["password", "token", "api_key", "secret"]
                    for field in sensitive_fields:
                        if field in request_data:
                            request_data[field] = "[REDACTED]"
            except (json.JSONDecodeError, UnicodeDecodeError):
                request_data = {"error": "Could not parse request body"}

        logger.info(
            f"Request started: {request.method} {request.path}",
            extra={
                "request_id": request.request_id,
                "method": request.method,
                "path": request.path,
                "user_id": user_id,
                "ip_address": ip,
                "user_agent": request.META.get("HTTP_USER_AGENT", ""),
                "request_data": request_data,
                "query_params": dict(request.GET),
            },
        )

    def process_response(
        self, request: HttpRequest, response: HttpResponse
    ) -> HttpResponse:
        """Process outgoing response"""

        if hasattr(request, "start_time"):
            duration = time.time() - request.start_time

            # Log response details
            user_id = (
                getattr(request.user, "id", None)
                if hasattr(request, "user") and request.user.is_authenticated
                else None
            )

            # Prepare response data (limit size)
            response_data = {}
            if hasattr(response, "data"):
                response_data = response.data
            elif response.get("Content-Type", "").startswith("application/json"):
                try:
                    response_content = response.content.decode("utf-8")
                    if len(response_content) < 1000:  # Only log small responses
                        response_data = json.loads(response_content)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass

            log_level = logging.INFO
            if response.status_code >= 400:
                log_level = (
                    logging.WARNING if response.status_code < 500 else logging.ERROR
                )

            logger.log(
                log_level,
                f"Request completed: {request.method} {request.path} - {response.status_code}",
                extra={
                    "request_id": getattr(request, "request_id", "unknown"),
                    "method": request.method,
                    "path": request.path,
                    "status_code": response.status_code,
                    "duration": round(duration, 3),
                    "user_id": user_id,
                    "response_data": response_data,
                },
            )

        return response

    def process_exception(
        self, request: HttpRequest, exception: Exception
    ) -> Optional[HttpResponse]:
        """Process unhandled exceptions"""

        duration = time.time() - getattr(request, "start_time", time.time())
        user_id = (
            getattr(request.user, "id", None)
            if hasattr(request, "user") and request.user.is_authenticated
            else None
        )

        logger.error(
            f"Request failed: {request.method} {request.path} - {type(exception).__name__}: {str(exception)}",
            extra={
                "request_id": getattr(request, "request_id", "unknown"),
                "method": request.method,
                "path": request.path,
                "duration": round(duration, 3),
                "user_id": user_id,
                "exception_type": type(exception).__name__,
                "exception_message": str(exception),
            },
            exc_info=True,
        )

        return None


class RateLimitMiddleware(MiddlewareMixin):
    """Middleware for API rate limiting"""

    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)

    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Check rate limits for incoming requests"""

        # Only apply rate limiting to API endpoints
        if not request.path.startswith("/api/"):
            return None

        # Get rate limit configuration
        rate_limits = getattr(settings, "RATE_LIMITS", {})

        # Determine rate limit based on user type
        if hasattr(request, "user") and request.user.is_authenticated:
            if request.user.is_superuser:
                limit_config = rate_limits.get(
                    "superuser", {"requests": 10000, "window": 3600}
                )
            else:
                limit_config = rate_limits.get(
                    "authenticated", {"requests": 1000, "window": 3600}
                )
            identifier = f"user:{request.user.id}"
        else:
            limit_config = rate_limits.get(
                "anonymous", {"requests": 100, "window": 3600}
            )
            # Use IP address for anonymous users
            x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
            if x_forwarded_for:
                ip = x_forwarded_for.split(",")[0]
            else:
                ip = request.META.get("REMOTE_ADDR", "unknown")
            identifier = f"ip:{ip}"

        # Check rate limit
        if self._is_rate_limited(identifier, limit_config):
            error_data = {
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": (
                        f"Rate limit exceeded: {limit_config['requests']} requests"
                        f" per {limit_config['window']} seconds"
                    ),
                    "details": {
                        "limit": limit_config["requests"],
                        "window": limit_config["window"],
                        "retry_after": limit_config["window"],
                    },
                }
            }
            return JsonResponse(error_data, status=429)

        return None

    def _is_rate_limited(self, identifier: str, limit_config: Dict[str, int]) -> bool:
        """Check if identifier has exceeded rate limit"""

        cache_key = f"rate_limit:{identifier}"
        current_requests = cache.get(cache_key, 0)

        if current_requests >= limit_config["requests"]:
            return True

        # Increment counter
        try:
            cache.set(cache_key, current_requests + 1, limit_config["window"])
        except Exception as e:
            logger.warning(f"Failed to update rate limit cache: {e}")
            # Allow request if cache fails
            return False

        return False


class APIKeyAuthenticationMiddleware(MiddlewareMixin):
    """Middleware for API key authentication"""

    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Authenticate requests using API key"""

        # Only apply to API endpoints that require API key auth
        if not request.path.startswith("/api/") or request.path.startswith(
            "/api/auth/"
        ):
            return None

        # Check for API key in headers
        api_key = request.META.get("HTTP_X_API_KEY") or request.META.get(
            "HTTP_AUTHORIZATION"
        )

        if api_key:
            # Remove 'Bearer ' prefix if present
            if api_key.startswith("Bearer "):
                api_key = api_key[7:]

            # Try to authenticate with API key
            try:
                # Check if it's a valid token
                token = Token.objects.select_related("user").get(key=api_key)
                request.user = token.user
                request.auth = token

                # Log API key usage
                logger.info(
                    f"API key authentication successful for user {token.user.id}",
                    extra={
                        "user_id": token.user.id,
                        "api_key_prefix": api_key[:8] + "...",
                        "path": request.path,
                        "method": request.method,
                    },
                )

            except Token.DoesNotExist:
                # Invalid API key
                logger.warning(
                    f"Invalid API key used: {api_key[:8]}...",
                    extra={
                        "api_key_prefix": api_key[:8] + "...",
                        "path": request.path,
                        "method": request.method,
                        "ip_address": request.META.get("REMOTE_ADDR"),
                    },
                )

                error_data = {
                    "error": {
                        "code": "INVALID_API_KEY",
                        "message": "Invalid API key provided",
                        "details": {},
                    }
                }
                return JsonResponse(error_data, status=401)

        return None


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Middleware for adding security headers"""

    def process_response(
        self, request: HttpRequest, response: HttpResponse
    ) -> HttpResponse:
        """Add security headers to response"""

        # Add security headers
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Frame-Options"] = "DENY"
        response["X-XSS-Protection"] = "1; mode=block"
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Add CORS headers for API endpoints
        if request.path.startswith("/api/"):
            response["Access-Control-Allow-Origin"] = getattr(
                settings, "CORS_ALLOWED_ORIGINS", ["http://localhost:3000"]
            )[0]
            response[
                "Access-Control-Allow-Methods"
            ] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            response[
                "Access-Control-Allow-Headers"
            ] = "Content-Type, Authorization, X-API-Key"
            response["Access-Control-Max-Age"] = "86400"

        return response


class HealthCheckMiddleware(MiddlewareMixin):
    """Middleware for health check endpoints"""

    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Handle health check requests"""

        if request.path == "/health/" or request.path == "/api/health/":
            # Simple health check
            health_data = {
                "status": "healthy",
                "timestamp": time.time(),
                "version": getattr(settings, "VERSION", "1.0.0"),
            }

            # Add database check
            try:
                from django.db import connection

                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                health_data["database"] = "connected"
            except Exception as e:
                health_data["database"] = f"error: {str(e)}"
                health_data["status"] = "unhealthy"

            # Add cache check
            try:
                cache.set("health_check", "ok", 10)
                if cache.get("health_check") == "ok":
                    health_data["cache"] = "connected"
                else:
                    health_data["cache"] = "error: cache test failed"
                    health_data["status"] = "unhealthy"
            except Exception as e:
                health_data["cache"] = f"error: {str(e)}"
                health_data["status"] = "unhealthy"

            base_dir = getattr(settings, "BASE_DIR", os.getcwd())
            try:
                usage = shutil.disk_usage(str(base_dir))
                total = float(usage.total) if usage.total else 0.0
                used = float(usage.used) if usage.used else 0.0
                disk_percent = (used / total) * 100 if total else 0.0
                health_data["storage"] = {
                    "total_bytes": int(usage.total),
                    "used_bytes": int(usage.used),
                    "free_bytes": int(usage.free),
                    "used_percent": round(disk_percent, 2),
                    "path": str(base_dir),
                }
            except Exception as e:
                health_data["storage"] = {"error": str(e), "path": str(base_dir)}

            try:
                import psutil  # type: ignore

                health_data["system"] = {
                    "cpu_percent": round(float(psutil.cpu_percent(interval=0.0)), 2),
                    "memory_percent": round(float(psutil.virtual_memory().percent), 2),
                }
            except Exception:
                health_data["system"] = {"cpu_percent": None, "memory_percent": None}

            status_code = 200 if health_data["status"] == "healthy" else 503
            return JsonResponse(health_data, status=status_code)

        return None


class RequestSizeMiddleware(MiddlewareMixin):
    """Middleware for limiting request size"""

    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Check request size limits"""

        # Get max request size from settings
        max_size = getattr(
            settings, "MAX_REQUEST_SIZE", 10 * 1024 * 1024
        )  # 10MB default

        # Check content length
        content_length = request.META.get("CONTENT_LENGTH")
        if content_length:
            try:
                content_length = int(content_length)
                if content_length > max_size:
                    error_data = {
                        "error": {
                            "code": "REQUEST_TOO_LARGE",
                            "message": (
                                f"Request size ({content_length} bytes) exceeds"
                                f" maximum allowed size ({max_size} bytes)"
                            ),
                            "details": {
                                "max_size": max_size,
                                "request_size": content_length,
                            },
                        }
                    }
                    return JsonResponse(error_data, status=413)
            except ValueError:
                pass

        return None


class CacheControlMiddleware(MiddlewareMixin):
    """Middleware for setting cache control headers"""

    def process_response(
        self, request: HttpRequest, response: HttpResponse
    ) -> HttpResponse:
        """Set appropriate cache control headers"""

        # Don't cache API responses by default
        if request.path.startswith("/api/"):
            # Check if response is cacheable
            if (
                response.status_code == 200
                and request.method == "GET"
                and not hasattr(request, "user")
                or not request.user.is_authenticated
            ):
                # Cache public endpoints for a short time
                if any(
                    endpoint in request.path
                    for endpoint in ["/api/transforms/", "/api/tools/"]
                ):
                    response["Cache-Control"] = "public, max-age=300"  # 5 minutes
                else:
                    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
            else:
                response["Cache-Control"] = "no-cache, no-store, must-revalidate"

            response["Pragma"] = "no-cache"
            response["Expires"] = "0"

        return response
