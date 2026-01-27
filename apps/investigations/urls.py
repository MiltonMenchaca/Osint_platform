from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()

urlpatterns = [
    path("", include(router.urls)),
    # Investigation endpoints
    path(
        "investigations/",
        views.InvestigationListCreateView.as_view(),
        name="investigation-list-create",
    ),
    path(
        "investigations/<uuid:pk>/",
        views.InvestigationDetailView.as_view(),
        name="investigation-detail",
    ),
    path(
        "investigations/<uuid:investigation_id>/stats/",
        views.investigation_stats,
        name="investigation-stats",
    ),
    path(
        "investigations/<uuid:investigation_id>/export/",
        views.investigation_export,
        name="investigation-export",
    ),
    # Transform execution endpoints
    path(
        "investigations/<uuid:investigation_id>/executions/",
        views.TransformExecutionListCreateView.as_view(),
        name="execution-list-create",
    ),
    path(
        "investigations/<uuid:investigation_id>/executions/<uuid:pk>/",
        views.TransformExecutionDetailView.as_view(),
        name="execution-detail",
    ),
    path(
        "investigations/<uuid:investigation_id>/executions/<uuid:execution_id>/control/",
        views.control_execution,
        name="execution-control",
    ),
    path(
        "investigations/<uuid:investigation_id>/executions/<uuid:execution_id>/logs/",
        views.execution_logs,
        name="execution-logs",
    ),
    # Bulk operations
    path(
        "investigations/<uuid:investigation_id>/bulk-execute/",
        views.bulk_execute_transforms,
        name="bulk-execute-transforms",
    ),
    # User statistics
    path(
        "user/stats/", views.user_investigations_stats, name="user-investigations-stats"
    ),
]
