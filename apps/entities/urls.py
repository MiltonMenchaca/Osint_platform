from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    EntityDetailView,
    EntityListCreateView,
    RelationshipDetailView,
    RelationshipListCreateView,
    all_entities,
    entity_graph,
    entity_relationships,
    entity_stats,
    entity_types,
    geo_events,
    merge_entities,
    validate_entities,
)

router = DefaultRouter()

# Register viewsets with router (commented out - using class-based views instead)
# router.register(r'entities', EntityViewSet, basename='entity')
# router.register(r'relationships', RelationshipViewSet, basename='relationship')

urlpatterns = [
    path("", include(router.urls)),
    # General entities endpoint (all user entities)
    path("entities/", all_entities, name="all-entities"),
    path("entities/types/", entity_types, name="entity-types"),
    path("events/geo/", geo_events, name="events-geo"),
    # Investigation-specific entity endpoints
    path(
        "investigations/<uuid:investigation_id>/entities/",
        EntityListCreateView.as_view(),
        name="entity-list-create",
    ),
    path(
        "investigations/<uuid:investigation_id>/entities/<uuid:pk>/",
        EntityDetailView.as_view(),
        name="entity-detail",
    ),
    # Investigation-specific relationship endpoints
    path(
        "investigations/<uuid:investigation_id>/relationships/",
        RelationshipListCreateView.as_view(),
        name="relationship-list-create",
    ),
    path(
        "investigations/<uuid:investigation_id>/relationships/<uuid:pk>/",
        RelationshipDetailView.as_view(),
        name="relationship-detail",
    ),
    # Additional entity operations
    path(
        "investigations/<uuid:investigation_id>/entities/stats/",
        entity_stats,
        name="entity-stats",
    ),
    path(
        "investigations/<uuid:investigation_id>/entities/<uuid:entity_id>/relationships/",
        entity_relationships,
        name="entity-relationships",
    ),
    path(
        "investigations/<uuid:investigation_id>/entities/merge/",
        merge_entities,
        name="entity-merge",
    ),
    path(
        "investigations/<uuid:investigation_id>/entities/graph/",
        entity_graph,
        name="entity-graph",
    ),
    path(
        "investigations/<uuid:investigation_id>/entities/validate/",
        validate_entities,
        name="validate-entities",
    ),
]
