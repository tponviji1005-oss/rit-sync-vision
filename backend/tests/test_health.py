"""
Unit tests for API health check endpoints.
"""


def test_root_health_check(client):
    """Verify preserved root health check returns HTTP 200 and expected payload."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "rit-sync-vision-backend"


def test_versioned_health_check(client):
    """Verify versioned /api/v1/health returns HTTP 200, v1 tag, and expected payload."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "rit-sync-vision-backend"
    assert data["version"] == "v1"
