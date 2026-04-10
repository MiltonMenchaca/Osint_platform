"""Custom exceptions for OSINT platform"""

import logging
from typing import Any, Dict

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


# Base exceptions
class OSINTBaseException(Exception):
    """Base exception for OSINT platform"""

    def __init__(self, message: str, code: str = None, details: Dict[str, Any] = None):
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary"""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }


# Authentication exceptions
class AuthenticationError(OSINTBaseException):
    """Authentication related errors"""

    pass


class InvalidCredentialsError(AuthenticationError):
    """Invalid login credentials"""

    def __init__(self, message: str = "Invalid credentials provided"):
        super().__init__(message, "INVALID_CREDENTIALS")


class TokenExpiredError(AuthenticationError):
    """JWT token has expired"""

    def __init__(self, message: str = "Authentication token has expired"):
        super().__init__(message, "TOKEN_EXPIRED")


class InvalidTokenError(AuthenticationError):
    """Invalid JWT token"""

    def __init__(self, message: str = "Invalid authentication token"):
        super().__init__(message, "INVALID_TOKEN")


class InsufficientPermissionsError(AuthenticationError):
    """User lacks required permissions"""

    def __init__(
        self,
        message: str = "Insufficient permissions for this operation",
        required_permission: str = None,
    ):
        details = {}
        if required_permission:
            details["required_permission"] = required_permission
        super().__init__(message, "INSUFFICIENT_PERMISSIONS", details)


# Investigation exceptions
class InvestigationError(OSINTBaseException):
    """Investigation related errors"""

    pass


class InvestigationNotFoundError(InvestigationError):
    """Investigation not found"""

    def __init__(self, investigation_id: int):
        message = f"Investigation with ID {investigation_id} not found"
        details = {"investigation_id": investigation_id}
        super().__init__(message, "INVESTIGATION_NOT_FOUND", details)


class InvestigationAccessDeniedError(InvestigationError):
    """Access denied to investigation"""

    def __init__(self, investigation_id: int, user_id: int):
        message = f"Access denied to investigation {investigation_id}"
        details = {"investigation_id": investigation_id, "user_id": user_id}
        super().__init__(message, "INVESTIGATION_ACCESS_DENIED", details)


class InvestigationLimitExceededError(InvestigationError):
    """User has exceeded investigation limit"""

    def __init__(self, current_count: int, max_allowed: int):
        message = f"Investigation limit exceeded ({current_count}/{max_allowed})"
        details = {"current_count": current_count, "max_allowed": max_allowed}
        super().__init__(message, "INVESTIGATION_LIMIT_EXCEEDED", details)


# Transform exceptions
class TransformError(OSINTBaseException):
    """Transform related errors"""

    pass


class TransformNotFoundError(TransformError):
    """Transform not found"""

    def __init__(self, transform_name: str):
        message = f"Transform '{transform_name}' not found"
        details = {"transform_name": transform_name}
        super().__init__(message, "TRANSFORM_NOT_FOUND", details)


class TransformExecutionError(TransformError):
    """Transform execution failed"""

    def __init__(self, transform_name: str, error_message: str, execution_id: str = None):
        message = f"Transform '{transform_name}' execution failed: {error_message}"
        details = {"transform_name": transform_name, "error_message": error_message}
        if execution_id:
            details["execution_id"] = execution_id
        super().__init__(message, "TRANSFORM_EXECUTION_FAILED", details)


class TransformTimeoutError(TransformError):
    """Transform execution timed out"""

    def __init__(self, transform_name: str, timeout_seconds: int, execution_id: str = None):
        message = f"Transform '{transform_name}' timed out after {timeout_seconds} seconds"
        details = {"transform_name": transform_name, "timeout_seconds": timeout_seconds}
        if execution_id:
            details["execution_id"] = execution_id
        super().__init__(message, "TRANSFORM_TIMEOUT", details)


class TransformConfigurationError(TransformError):
    """Transform configuration is invalid"""

    def __init__(self, transform_name: str, config_errors: Dict[str, Any]):
        message = f"Transform '{transform_name}' has invalid configuration"
        details = {"transform_name": transform_name, "config_errors": config_errors}
        super().__init__(message, "TRANSFORM_CONFIGURATION_ERROR", details)


class TransformInputValidationError(TransformError):
    """Transform input validation failed"""

    def __init__(self, transform_name: str, validation_errors: Dict[str, Any]):
        message = f"Transform '{transform_name}' input validation failed"
        details = {
            "transform_name": transform_name,
            "validation_errors": validation_errors,
        }
        super().__init__(message, "TRANSFORM_INPUT_VALIDATION_ERROR", details)


# Tool exceptions
class ToolError(OSINTBaseException):
    """OSINT tool related errors"""

    pass


class ToolNotFoundError(ToolError):
    """OSINT tool not found or not installed"""

    def __init__(self, tool_name: str, install_instructions: str = None):
        message = f"OSINT tool '{tool_name}' not found or not installed"
        details = {"tool_name": tool_name}
        if install_instructions:
            details["install_instructions"] = install_instructions
        super().__init__(message, "TOOL_NOT_FOUND", details)


class ToolExecutionError(ToolError):
    """OSINT tool execution failed"""

    def __init__(self, tool_name: str, command: str, exit_code: int, stderr: str = None):
        message = f"Tool '{tool_name}' execution failed with exit code {exit_code}"
        details = {"tool_name": tool_name, "command": command, "exit_code": exit_code}
        if stderr:
            details["stderr"] = stderr
        super().__init__(message, "TOOL_EXECUTION_ERROR", details)


class ToolTimeoutError(ToolError):
    """OSINT tool execution timed out"""

    def __init__(self, tool_name: str, timeout_seconds: int):
        message = f"Tool '{tool_name}' execution timed out after {timeout_seconds} seconds"
        details = {"tool_name": tool_name, "timeout_seconds": timeout_seconds}
        super().__init__(message, "TOOL_TIMEOUT", details)


# Entity exceptions
class EntityError(OSINTBaseException):
    """Entity related errors"""

    pass


class EntityNotFoundError(EntityError):
    """Entity not found"""

    def __init__(self, entity_id: int):
        message = f"Entity with ID {entity_id} not found"
        details = {"entity_id": entity_id}
        super().__init__(message, "ENTITY_NOT_FOUND", details)


class EntityValidationError(EntityError):
    """Entity validation failed"""

    def __init__(self, validation_errors: Dict[str, Any]):
        message = "Entity validation failed"
        details = {"validation_errors": validation_errors}
        super().__init__(message, "ENTITY_VALIDATION_ERROR", details)


class DuplicateEntityError(EntityError):
    """Duplicate entity detected"""

    def __init__(self, entity_type: str, entity_value: str, existing_id: int):
        message = f"Duplicate entity detected: {entity_type}:{entity_value}"
        details = {
            "entity_type": entity_type,
            "entity_value": entity_value,
            "existing_id": existing_id,
        }
        super().__init__(message, "DUPLICATE_ENTITY", details)


# Rate limiting exceptions
class RateLimitError(OSINTBaseException):
    """Rate limit exceeded"""

    def __init__(self, limit: int, window: int, retry_after: int = None):
        message = f"Rate limit exceeded: {limit} requests per {window} seconds"
        details = {"limit": limit, "window": window}
        if retry_after:
            details["retry_after"] = retry_after
        super().__init__(message, "RATE_LIMIT_EXCEEDED", details)


# API exceptions
class APIError(OSINTBaseException):
    """API related errors"""

    pass


class InvalidAPIKeyError(APIError):
    """Invalid API key provided"""

    def __init__(self, service_name: str):
        message = f"Invalid API key for service: {service_name}"
        details = {"service_name": service_name}
        super().__init__(message, "INVALID_API_KEY", details)


class APIQuotaExceededError(APIError):
    """API quota exceeded"""

    def __init__(self, service_name: str, quota_type: str, reset_time: str = None):
        message = f"API quota exceeded for {service_name}: {quota_type}"
        details = {"service_name": service_name, "quota_type": quota_type}
        if reset_time:
            details["reset_time"] = reset_time
        super().__init__(message, "API_QUOTA_EXCEEDED", details)


# Data processing exceptions
class DataProcessingError(OSINTBaseException):
    """Data processing errors"""

    pass


class DataParsingError(DataProcessingError):
    """Data parsing failed"""

    def __init__(self, data_type: str, error_message: str):
        message = f"Failed to parse {data_type} data: {error_message}"
        details = {"data_type": data_type, "error_message": error_message}
        super().__init__(message, "DATA_PARSING_ERROR", details)


class DataValidationError(DataProcessingError):
    """Data validation failed"""

    def __init__(self, validation_errors: Dict[str, Any]):
        message = "Data validation failed"
        details = {"validation_errors": validation_errors}
        super().__init__(message, "DATA_VALIDATION_ERROR", details)


# Custom exception handler for DRF
def custom_exception_handler(exc, context):
    """Custom exception handler for Django REST Framework"""

    # Get the standard error response first
    response = exception_handler(exc, context)

    # Log the exception
    request = context.get("request")
    view = context.get("view")

    logger.error(
        f"Exception in {view.__class__.__name__ if view else 'Unknown'}: {str(exc)}",
        extra={
            "exception_type": type(exc).__name__,
            "request_path": request.path if request else None,
            "request_method": request.method if request else None,
            "user_id": getattr(request.user, "id", None) if request and hasattr(request, "user") else None,
        },
        exc_info=True,
    )

    # Handle custom OSINT exceptions
    if isinstance(exc, OSINTBaseException):
        return Response(exc.to_dict(), status=get_status_code_for_exception(exc))

    # Handle Django validation errors
    if isinstance(exc, ValidationError):
        error_data = {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Validation failed",
                "details": {"validation_errors": exc.message_dict if hasattr(exc, "message_dict") else [str(exc)]},
            }
        }
        return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

    # Customize standard DRF error responses
    if response is not None:
        custom_response_data = {
            "error": {
                "code": get_error_code_from_status(response.status_code),
                "message": get_error_message_from_status(response.status_code),
                "details": response.data,
            }
        }
        response.data = custom_response_data

    return response


def get_status_code_for_exception(exc: OSINTBaseException) -> int:
    """Get appropriate HTTP status code for custom exception"""

    status_map = {
        # Authentication errors
        "INVALID_CREDENTIALS": status.HTTP_401_UNAUTHORIZED,
        "TOKEN_EXPIRED": status.HTTP_401_UNAUTHORIZED,
        "INVALID_TOKEN": status.HTTP_401_UNAUTHORIZED,
        "INSUFFICIENT_PERMISSIONS": status.HTTP_403_FORBIDDEN,
        # Investigation errors
        "INVESTIGATION_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "INVESTIGATION_ACCESS_DENIED": status.HTTP_403_FORBIDDEN,
        "INVESTIGATION_LIMIT_EXCEEDED": status.HTTP_429_TOO_MANY_REQUESTS,
        # Transform errors
        "TRANSFORM_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "TRANSFORM_EXECUTION_FAILED": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "TRANSFORM_TIMEOUT": status.HTTP_408_REQUEST_TIMEOUT,
        "TRANSFORM_CONFIGURATION_ERROR": status.HTTP_400_BAD_REQUEST,
        "TRANSFORM_INPUT_VALIDATION_ERROR": status.HTTP_400_BAD_REQUEST,
        # Tool errors
        "TOOL_NOT_FOUND": status.HTTP_503_SERVICE_UNAVAILABLE,
        "TOOL_EXECUTION_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "TOOL_TIMEOUT": status.HTTP_408_REQUEST_TIMEOUT,
        # Entity errors
        "ENTITY_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "ENTITY_VALIDATION_ERROR": status.HTTP_400_BAD_REQUEST,
        "DUPLICATE_ENTITY": status.HTTP_409_CONFLICT,
        # Rate limiting
        "RATE_LIMIT_EXCEEDED": status.HTTP_429_TOO_MANY_REQUESTS,
        # API errors
        "INVALID_API_KEY": status.HTTP_401_UNAUTHORIZED,
        "API_QUOTA_EXCEEDED": status.HTTP_429_TOO_MANY_REQUESTS,
        # Data processing errors
        "DATA_PARSING_ERROR": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "DATA_VALIDATION_ERROR": status.HTTP_400_BAD_REQUEST,
    }

    return status_map.get(exc.code, status.HTTP_500_INTERNAL_SERVER_ERROR)


def get_error_code_from_status(status_code: int) -> str:
    """Get error code from HTTP status code"""

    code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        408: "REQUEST_TIMEOUT",
        409: "CONFLICT",
        422: "UNPROCESSABLE_ENTITY",
        429: "TOO_MANY_REQUESTS",
        500: "INTERNAL_SERVER_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
        504: "GATEWAY_TIMEOUT",
    }

    return code_map.get(status_code, "UNKNOWN_ERROR")


def get_error_message_from_status(status_code: int) -> str:
    """Get error message from HTTP status code"""

    message_map = {
        400: "Bad request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not found",
        405: "Method not allowed",
        408: "Request timeout",
        409: "Conflict",
        422: "Unprocessable entity",
        429: "Too many requests",
        500: "Internal server error",
        502: "Bad gateway",
        503: "Service unavailable",
        504: "Gateway timeout",
    }

    return message_map.get(status_code, "Unknown error")


# Middleware for global error handling
class ErrorHandlingMiddleware:
    """Middleware for global error handling"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
            return response
        except Exception as exc:
            # Log unexpected errors
            logger.error(
                f"Unexpected error in middleware: {str(exc)}",
                extra={
                    "exception_type": type(exc).__name__,
                    "request_path": request.path,
                    "request_method": request.method,
                    "user_id": getattr(request.user, "id", None) if hasattr(request, "user") else None,
                },
                exc_info=True,
            )

            # Return JSON error response for API requests
            if request.path.startswith("/api/"):
                error_data = {
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An unexpected error occurred",
                        "details": {},
                    }
                }
                return JsonResponse(error_data, status=500)

            # Re-raise for non-API requests
            raise
