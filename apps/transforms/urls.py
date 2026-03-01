from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
# router.register(r'transforms', views.TransformViewSet)
# router.register(r'categories', views.CategoryViewSet)

urlpatterns = [
    path("", include(router.urls)),
    # Transform management endpoints
    path(
        "transforms/",
        views.TransformListCreateView.as_view(),
        name="transform-list-create",
    ),
    path(
        "transforms/<uuid:pk>/",
        views.TransformDetailView.as_view(),
        name="transform-detail",
    ),
    path("transforms/stats/", views.transform_stats, name="transform-stats"),
    path("transforms/<uuid:pk>/test/", views.test_transform, name="test-transform"),
    path(
        "transforms/<uuid:pk>/validate/",
        views.validate_transform,
        name="validate-transform",
    ),
    path(
        "transforms/<uuid:pk>/usage-stats/",
        views.transform_usage_stats,
        name="transform-usage-stats",
    ),
    # Bulk operations
    path(
        "transforms/bulk-actions/",
        views.bulk_transform_actions,
        name="bulk-transform-actions",
    ),
    path("transforms/import/", views.import_transforms, name="import-transforms"),
    path("transforms/export/", views.export_transforms, name="export-transforms"),
    # Categories
    path("categories/", views.transform_categories, name="transform-categories"),
    # Specific transform endpoints
    path("holehe/execute/", views.execute_holehe, name="execute-holehe"),
]
