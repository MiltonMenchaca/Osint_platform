import os

import django


def test_django_settings_loaded():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "osint_platform.settings.development")
    django.setup()
    from django.conf import settings

    assert settings.configured


def test_user_stats_endpoint_shape(db, django_user_model):
    from rest_framework.test import APIClient

    from apps.entities.models import Entity
    from apps.investigations.models import Investigation, TransformExecution

    user = django_user_model.objects.create_user(username="u1", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)

    investigation = Investigation.objects.create(
        name="inv1", description="", status="active", created_by=user
    )
    entity = Entity.objects.create(investigation=investigation, entity_type="domain", value="example.com")
    TransformExecution.objects.create(
        investigation=investigation,
        transform_name="subfinder",
        input_entity=entity,
        status="completed",
        results={"ok": True},
    )

    response = client.get("/api/user/stats/")
    assert response.status_code == 200
    data = response.json()

    assert data["investigations"]["total"] == 1
    assert data["investigations"]["by_status"]["active"] == 1
    assert data["executions"]["total"] == 1
    assert data["entities"]["total"] == 1
    assert data["entities"]["by_type"]["domain"] == 1


def test_auth_user_stats_includes_entities_and_recent(db, django_user_model):
    from rest_framework.test import APIClient

    from apps.entities.models import Entity
    from apps.investigations.models import Investigation, TransformExecution

    user = django_user_model.objects.create_user(username="u2", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)

    investigation = Investigation.objects.create(
        name="inv2", description="", status="active", created_by=user
    )
    entity = Entity.objects.create(investigation=investigation, entity_type="domain", value="example.org")
    TransformExecution.objects.create(
        investigation=investigation,
        transform_name="assetfinder",
        input_entity=entity,
        status="running",
        results={},
    )

    response = client.get("/api/auth/user/stats/")
    assert response.status_code == 200
    data = response.json()

    assert "by_status" in data["investigations"]
    assert data["investigations"]["by_status"]["active"] == 1
    assert data["investigations"]["recent"] == 1

    assert "by_type" in data["entities"]
    assert data["entities"]["by_type"]["domain"] == 1
    assert data["entities"]["recent"] == 1

    assert data["executions"]["total"] == 1
    assert data["executions"]["running"] == 1
    assert data["executions"]["recent"] == 1


def test_subfinder_wrapper_formats_output(monkeypatch):
    from apps.transforms.wrappers.base import BaseWrapper
    from apps.transforms.wrappers.subfinder import SubfinderWrapper

    def fake_find_tool_path(self):
        return "subfinder"

    def fake_run_command(self, command, timeout=300, input_data=None, cwd=None, env=None):
        return {
            "command": " ".join(command),
            "return_code": 0,
            "stdout": "a.example.com\na.example.com\nexample.com\nb.example.com\n",
            "stderr": "",
            "execution_time": 0.1,
            "start_time": "2026-01-01T00:00:00",
            "end_time": "2026-01-01T00:00:00",
        }

    monkeypatch.setattr(BaseWrapper, "_find_tool_path", fake_find_tool_path, raising=True)
    monkeypatch.setattr(BaseWrapper, "_run_command", fake_run_command, raising=True)

    wrapper = SubfinderWrapper()
    output = wrapper.execute({"type": "domain", "value": "example.com"})

    assert output["tool"] == "subfinder"
    assert output["input_type"] == "domain"
    assert output["input_value"] == "example.com"
    assert output["metadata"]["result_count"] == 2
    assert {r["value"] for r in output["results"]} == {"a.example.com", "b.example.com"}
