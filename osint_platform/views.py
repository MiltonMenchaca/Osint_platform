import logging

import django
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger("apps")


@csrf_exempt
def home_view(request):
    """Vista principal que muestra información básica de la plataforma OSINT"""
    return JsonResponse(
        {
            "project": "OSINT Platform",
            "version": "1.0.0",
            "description": "Plataforma de inteligencia de fuentes abiertas",
            "status": "running",
            "django_version": django.get_version(),
            "debug_mode": settings.DEBUG,
            "endpoints": {
                "admin": "/admin/",
                "api_status": "/api/status/",
                "authentication": {
                    "token_obtain": "/api/auth/token/",
                    "token_refresh": "/api/auth/token/refresh/",
                    "token_verify": "/api/auth/token/verify/",
                },
                "api": {
                    "investigations": "/api/investigations/",
                    "entities": "/api/entities/",
                    "transforms": "/api/transforms/",
                    "auth": "/api/auth/",
                },
                "documentation": "/api/docs/",
            },
        }
    )


@csrf_exempt
def bad_request(request, exception=None):
    """Handle 400 Bad Request errors"""
    logger.warning(f"Bad request: {request.path} - {exception}")
    return JsonResponse(
        {
            "error": "Bad Request",
            "message": "The request could not be understood by the server.",
            "status_code": 400,
        },
        status=400,
    )


@csrf_exempt
def permission_denied(request, exception=None):
    """Handle 403 Permission Denied errors"""
    logger.warning(f"Permission denied: {request.path} - {exception}")
    return JsonResponse(
        {
            "error": "Permission Denied",
            "message": "You do not have permission to access this resource.",
            "status_code": 403,
        },
        status=403,
    )


@csrf_exempt
def page_not_found(request, exception=None):
    """Handle 404 Not Found errors"""
    logger.info(f"Page not found: {request.path}")
    return JsonResponse(
        {
            "error": "Not Found",
            "message": "The requested resource was not found.",
            "status_code": 404,
        },
        status=404,
    )


@csrf_exempt
def server_error(request):
    """Handle 500 Internal Server Error"""
    logger.error(f"Server error: {request.path}")
    return JsonResponse(
        {
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Please try again later.",
            "status_code": 500,
        },
        status=500,
    )
