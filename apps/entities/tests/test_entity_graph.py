import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.entities.models import Entity, Relationship
from apps.investigations.models import Investigation


@pytest.mark.django_db
def test_entity_graph_returns_nodes_and_edges():
    User = get_user_model()
    user = User.objects.create_user(username="graph", password="password")
    investigation = Investigation.objects.create(
        name="Graph",
        description="Graph",
        created_by=user,
    )

    source = Entity.objects.create(
        investigation=investigation,
        entity_type="domain",
        value="example.com",
        source="manual",
    )
    target = Entity.objects.create(
        investigation=investigation,
        entity_type="ip",
        value="1.2.3.4",
        source="manual",
    )
    Relationship.objects.create(
        investigation=investigation,
        source_entity=source,
        target_entity=target,
        relationship_type="associated_with",
        confidence_score=0.8,
    )

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(f"/api/investigations/{investigation.id}/entities/graph/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["stats"]["node_count"] == 2
    assert payload["stats"]["edge_count"] == 1
