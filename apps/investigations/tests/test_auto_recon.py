import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.investigations.models import Investigation


@pytest.mark.django_db
def test_auto_recon_persists_metadata_and_entities(monkeypatch):
    User = get_user_model()
    user = User.objects.create_user(username="tester", password="password")
    investigation = Investigation.objects.create(
        name="Test",
        description="Test",
        created_by=user,
    )

    def fake_run_scan(self, target):
        return {
            "target": target,
            "status": "completed",
            "tools": {
                "wappalyzer": {
                    "results": [
                        {
                            "type": "technology",
                            "value": "Apache",
                            "properties": {"categories": ["Web Server"]},
                        }
                    ]
                },
                "nmap": {
                    "results": [
                        {
                            "type": "service",
                            "value": "http",
                            "properties": {"port": 80, "service_name": "http", "ip": "1.2.3.4"},
                        }
                    ]
                },
            },
        }

    from apps.investigations.services.auto_recon import AutoReconService

    monkeypatch.setattr(AutoReconService, "run_scan", fake_run_scan)

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        "/api/investigations/auto-recon/",
        {"target": "example.com", "investigation_id": str(investigation.id)},
        format="json",
    )

    assert response.status_code == 200

    investigation.refresh_from_db()
    assert investigation.metadata["auto_recon"]["status"] == "completed"
    assert "auto_recon_updated_at" in investigation.metadata

    from apps.entities.models import Entity, Relationship

    assert Entity.objects.filter(investigation=investigation).exists()
    assert Relationship.objects.filter(investigation=investigation).exists()
