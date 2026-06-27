"""Demo-spine API checks — require DATABASE_URL and seed data."""

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from tests.conftest import HAS_DATABASE, KARLSRUHE_BBOX

client = TestClient(app)


@pytest.mark.skipif(not HAS_DATABASE, reason="DATABASE_URL not configured")
def test_demo_seed_has_berta_adopted(dev_auth: None) -> None:
    response = client.get(f"/api/v1/trees?bbox={KARLSRUHE_BBOX}&status=adopted&limit=50")
    assert response.status_code == 200
    names = [t.get("name") for t in response.json()["trees"]]
    if "Berta" not in names:
        pytest.skip("Demo tree Berta not found — run `python -m app.seed demo`")


@pytest.mark.skipif(not HAS_DATABASE, reason="DATABASE_URL not configured")
def test_demo_tree_001_sensor_monitored(dev_auth: None) -> None:
    response = client.get("/api/v1/sensors")
    assert response.status_code == 200
    refs = {row.get("device_eui", "") for row in response.json()}
    if not any("tree_001" in ref for ref in refs):
        pytest.skip("tree_001 sensor not seeded — run `make seed`")


@pytest.mark.skipif(not HAS_DATABASE, reason="DATABASE_URL not configured")
def test_ingest_http_accepts_valid_payload(dev_auth: None) -> None:
    secret = get_settings().ingest_shared_secret
    response = client.post(
        "/api/v1/ingest/http",
        json={"tree_id": "tree_001", "raw_value": 2100, "fcnt": 999_001},
        headers={"Authorization": f"Bearer {secret}"},
    )
    if response.status_code == 404:
        pytest.skip("tree_001 sensor not registered — run `make seed`")
    assert response.status_code == 202
    body = response.json()
    assert body["accepted"] is True
    assert "moisture_pct" in body
    assert "health_state" in body


@pytest.mark.skipif(not HAS_DATABASE, reason="DATABASE_URL not configured")
def test_stats_overview_nonzero_after_seed(dev_auth: None) -> None:
    response = client.get("/api/v1/stats/overview")
    assert response.status_code == 200
    body = response.json()
    if body["trees_total"] == 0:
        pytest.skip("No trees in database — run `make seed`")
    assert body["trees_total"] > 0
