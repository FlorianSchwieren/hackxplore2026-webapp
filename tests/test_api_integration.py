"""API integration and contract tests (no DB required for core cases)."""

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.schemas import CoPartnersResponse, HealthzResponse, PredictionsResponse
from tests.conftest import HAS_DATABASE, KARLSRUHE_BBOX

client = TestClient(app)


# --- Health / liveness (no DB) ---


def test_healthz_root() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "time" in body


def test_healthz_api_prefix() -> None:
    response = client.get("/api/v1/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_healthz_response_schema() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    parsed = HealthzResponse.model_validate(response.json())
    assert parsed.status == "ok"
    assert parsed.time is not None


def test_healthz_api_prefix_matches_root_schema() -> None:
    root = HealthzResponse.model_validate(client.get("/healthz").json())
    api = HealthzResponse.model_validate(client.get("/api/v1/healthz").json())
    assert root.status == api.status == "ok"


# --- Auth gates (no DB) ---


def test_trees_requires_auth_when_dev_auth_off(auth_required: None) -> None:
    response = client.get(f"/api/v1/trees?bbox={KARLSRUHE_BBOX}")
    assert response.status_code == 401


def test_stats_overview_requires_auth_when_dev_auth_off(auth_required: None) -> None:
    response = client.get("/api/v1/stats/overview")
    assert response.status_code == 401


def test_co_partners_requires_auth_when_dev_auth_off(auth_required: None) -> None:
    response = client.get("/api/v1/me/co-partners")
    assert response.status_code == 401


def test_co_partners_empty_response_shape(dev_auth: None, mock_db_session: object) -> None:
    response = client.get("/api/v1/me/co-partners")
    assert response.status_code == 200
    parsed = CoPartnersResponse.model_validate(response.json())
    assert parsed.count == 0
    assert parsed.co_partners == []


# --- Ingest auth (no DB — rejected before session) ---


def test_ingest_http_rejects_bad_secret() -> None:
    response = client.post(
        "/api/v1/ingest/http",
        json={"tree_id": "tree_001", "raw_value": 2000},
        headers={"Authorization": "Bearer wrong-secret"},
    )
    assert response.status_code == 401


def test_ingest_http_rejects_missing_bearer() -> None:
    response = client.post(
        "/api/v1/ingest/http",
        json={"tree_id": "tree_001", "raw_value": 2000},
    )
    assert response.status_code == 401


def test_ingest_lorawan_rejects_bad_secret() -> None:
    response = client.post(
        "/api/v1/ingest/lorawan",
        json={"deviceInfo": {"devEui": "BAUMPATE-tree_001"}, "data": "AQID"},
        headers={"Authorization": "Bearer wrong-secret"},
    )
    assert response.status_code == 401


# --- Validation errors (mock session — no real DB) ---


def test_ingest_lorawan_malformed_payload(mock_db_session: object) -> None:
    secret = get_settings().ingest_shared_secret
    response = client.post(
        "/api/v1/ingest/lorawan",
        json={"deviceInfo": {"devEui": "BAUMPATE-tree_001"}, "data": "!!!"},
        headers={"Authorization": f"Bearer {secret}"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Malformed LoRaWAN uplink"


def test_trees_invalid_bbox_non_numeric(dev_auth: None, mock_db_session: object) -> None:
    response = client.get("/api/v1/trees?bbox=not-a-bbox")
    assert response.status_code == 400
    assert "bbox" in response.json()["detail"].lower()


def test_trees_invalid_bbox_inverted_bounds(dev_auth: None, mock_db_session: object) -> None:
    response = client.get("/api/v1/trees?bbox=8.45,49.03,8.35,48.98")
    assert response.status_code == 400
    assert response.json()["detail"] == "bbox bounds are invalid"


# --- Predictions stub shape (mock session — no real DB) ---


def test_predictions_response_mock_model(mock_db_session: object) -> None:
    response = client.get("/api/v1/predictions?horizon_days=7")
    assert response.status_code == 200
    parsed = PredictionsResponse.model_validate(response.json())
    assert parsed.model == "mock-v0"
    assert parsed.horizon_days == 7
    assert isinstance(parsed.items, list)
    assert isinstance(parsed.stadtteil_trend, list)


# --- Database-backed contract tests ---


@pytest.mark.skipif(not HAS_DATABASE, reason="DATABASE_URL not configured")
def test_stats_overview_shape(dev_auth: None) -> None:
    response = client.get("/api/v1/stats/overview")
    assert response.status_code == 200
    body = response.json()
    for key in (
        "trees_total",
        "trees_monitored",
        "users_total",
        "partnerships_active",
        "health_distribution",
        "sensors",
        "city_health_score",
        "absences_active",
    ):
        assert key in body


@pytest.mark.skipif(not HAS_DATABASE, reason="DATABASE_URL not configured")
def test_weather_forecast_public() -> None:
    response = client.get("/api/v1/weather/forecast")
    assert response.status_code == 200
    body = response.json()
    assert "current" in body
    assert "daily" in body


@pytest.mark.skipif(not HAS_DATABASE, reason="DATABASE_URL not configured")
def test_predictions_live_db() -> None:
    response = client.get("/api/v1/predictions?horizon_days=7")
    assert response.status_code == 200
    parsed = PredictionsResponse.model_validate(response.json())
    assert parsed.model == "mock-v0"


@pytest.mark.skipif(not HAS_DATABASE, reason="DATABASE_URL not configured")
def test_trees_bbox_returns_count(dev_auth: None) -> None:
    response = client.get(f"/api/v1/trees?bbox={KARLSRUHE_BBOX}")
    assert response.status_code == 200
    body = response.json()
    assert "count" in body
    assert "trees" in body
    assert body["count"] == len(body["trees"])
    assert body["count"] >= 0


@pytest.mark.skipif(not HAS_DATABASE, reason="DATABASE_URL not configured")
def test_sensors_list(dev_auth: None) -> None:
    response = client.get("/api/v1/sensors")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    if body:
        row = body[0]
        for key in ("id", "device_eui", "tree_id", "status", "stadtteil", "lon", "lat"):
            assert key in row


@pytest.mark.skipif(not HAS_DATABASE, reason="DATABASE_URL not configured")
def test_partnership_adopt_conflict_on_adopted_tree(dev_auth: None) -> None:
    listed = client.get(f"/api/v1/trees?bbox={KARLSRUHE_BBOX}&status=adopted&limit=5")
    assert listed.status_code == 200
    adopted = listed.json()["trees"]
    if not adopted:
        pytest.skip("No adopted trees in bbox — run `make seed` first")
    tree_id = adopted[0]["id"]
    response = client.post("/api/v1/partnerships", json={"tree_id": tree_id})
    assert response.status_code == 409
    assert "adopted" in response.json()["detail"].lower()


@pytest.mark.skipif(not HAS_DATABASE, reason="DATABASE_URL not configured")
def test_co_partners_returns_shared_tree_links(dev_auth: None) -> None:
    from sqlalchemy import text

    from app.auth import CurrentUser, require_user
    from app.db import session_context
    import app.main as main_module

    with session_context() as session:
        row = session.execute(
            text(
                """
                select tp1.user_id
                from tree_partnerships tp1
                join tree_partnerships tp2
                  on tp1.tree_id = tp2.tree_id
                 and tp2.user_id <> tp1.user_id
                 and (tp2.active_to is null or tp2.active_to >= current_date)
                where tp1.active_to is null or tp1.active_to >= current_date
                limit 1
                """
            )
        ).first()
    if not row:
        pytest.skip("No co-partners in database — run `make seed` first")

    def override_user() -> CurrentUser:
        return CurrentUser(id=row[0])

    for target in (main_module.app, main_module.api):
        target.dependency_overrides[require_user] = override_user
    try:
        response = client.get("/api/v1/me/co-partners")
    finally:
        for target in (main_module.app, main_module.api):
            target.dependency_overrides.pop(require_user, None)

    assert response.status_code == 200
    parsed = CoPartnersResponse.model_validate(response.json())
    assert parsed.count >= 1
    assert len(parsed.co_partners) == parsed.count
    partner = parsed.co_partners[0]
    assert partner.shared_trees >= 1
    assert len(partner.trees) == partner.shared_trees
    assert partner.trees[0].your_role
    assert partner.trees[0].their_role
    assert partner.trees[0].name
