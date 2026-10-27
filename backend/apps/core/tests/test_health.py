"""Core app tests."""
import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_health_ok(client):
    url = reverse("health")
    resp = client.get(url)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["database"] == "up"
