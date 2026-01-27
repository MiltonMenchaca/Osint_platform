from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from .views import home_view


# Health check endpoint
@csrf_exempt
@require_http_methods(["GET"])
def health_check(request):
    """Simple health check endpoint"""
    return JsonResponse(
        {
            "status": "healthy",
            "service": "OSINT Platform API",
            "version": "1.0.0",
        }
    )


# API Status endpoint
@csrf_exempt
@require_http_methods(["GET"])
def api_status(request):
    """API status and information endpoint"""
    return JsonResponse(
        {
            "api_version": "v1",
            "status": "active",
            "endpoints": {
                "auth": "/api/auth/",
                "investigations": "/api/investigations/",
                "entities": "/api/entities/",
                "transforms": "/api/transforms/",
                "health": "/health/",
            },
            "documentation": "/api/docs/",
        }
    )


urlpatterns = [
    # Home page
    path("", home_view, name="home"),
    # Admin interface
    path("admin/", admin.site.urls),
    # Health check endpoints
    path("health/", health_check, name="health_check"),
    path("api/status/", api_status, name="api_status"),
    # JWT Authentication endpoints
    path(
        "api/auth/token/",
        TokenObtainPairView.as_view(),
        name="token_obtain_pair",
    ),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    # API endpoints
    path("api/", include("apps.investigations.urls")),
    path("api/", include("apps.entities.urls")),
    path("api/", include("apps.transforms.urls")),
    path("api/auth/", include("apps.authentication.urls")),
    path("api/tools/", include("osint_tools.urls")),
    # API Documentation (if using DRF spectacular)
    path("api/docs/", include("rest_framework.urls")),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # Add debug toolbar if available
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
        ] + urlpatterns

# Custom error handlers
handler400 = "osint_platform.views.bad_request"
handler403 = "osint_platform.views.permission_denied"
handler404 = "osint_platform.views.page_not_found"
handler500 = "osint_platform.views.server_error"
