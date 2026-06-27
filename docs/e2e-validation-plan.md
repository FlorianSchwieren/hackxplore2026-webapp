# E2E Validation Plan — Baumpate Backend + React Dashboard

> Execute order: **unit → API contract → DB seed → ingestion spine → frontend wiring → browser QA**.

## Prerequisites

| Item | Purpose |
|---|---|
| `.env` with `DATABASE_URL`, Supabase keys, `INGEST_SHARED_SECRET` | Migrations, seed, live API |
| `DEV_AUTH_DISABLED=true` (local only) | Dashboard calls without Supabase JWT |
| `make migrate && make seed` | Real PostGIS + demo data |
| Backend `:8000`, frontend `:5173` | Local stack |

## Layer 1 — Unit & pure logic (no DB)

| ID | Case | Command |
|---|---|---|
| U1 | Calibration boundaries, round-trip | `pytest tests/test_calibration.py` |
| U2 | LoRaWAN encode/decode + schema validation | `pytest tests/test_lorawan.py` |
| U3 | Scoring 1000→909, freeze, rain carve-out | `pytest tests/test_scoring.py` |
| U4 | Flutter/webapp field mapping | `pytest tests/test_mapping.py` |

**Pass criteria:** all green, no skips.

## Layer 2 — API contract (TestClient / httpx)

| ID | Endpoint | Edge case |
|---|---|---|
| A1 | `GET /healthz`, `GET /api/v1/healthz` | 200 + `status=ok` |
| A2 | Protected routes without JWT | 401 when `DEV_AUTH_DISABLED=false` |
| A3 | Protected routes with dev auth | 200/404/422 when `DEV_AUTH_DISABLED=true` |
| A4 | `POST /ingest/http` wrong secret | 401 |
| A5 | `POST /ingest/lorawan` malformed body | 400 |
| A6 | `POST /partnerships` on adopted tree | 409 (no competition) |
| A7 | `GET /trees` invalid bbox | 400 |
| A8 | Ingest duplicate within dedupe window | idempotent 202, no double health move |
| A9 | Outlier raw value | stored, tree health unchanged |
| A10 | `GET /weather/forecast` | 200 + snapshot write (needs DB) |
| A11 | `GET /stats/overview` | shape matches docs/03 §8 (needs DB) |

**Pass criteria:** `pytest tests/test_api_integration.py` (DB cases skip without `DATABASE_URL`).

## Layer 3 — Database & seed (requires `DATABASE_URL`)

| ID | Step | Verify |
|---|---|---|
| D1 | `make migrate` | PostGIS, tables, RLS, append-only triggers |
| D2 | `python -m app.seed species && python -m app.seed trees` | City-center trees loaded |
| D3 | `python -m app.seed sensors readings users partnerships demo` | Demo Berta thirsty, `tree_001` sensor |
| D4 | Re-run `seed demo` | Idempotent authoritative reset |

## Layer 4 — Demo spine (API + scripts)

| ID | Flow | Expected |
|---|---|---|
| S1 | `POST /ingest/http` thirsty → watered (×2) | `health_state` healthy, `streak_awarded` |
| S2 | `scripts/fake_water.py` | Same as S1 (safety net) |
| S3 | `scripts/make_thirsty.py` | Berta back to thirsty |
| S4 | `python -m app.cron` twice same day | No double streak increment |
| S5 | `POST /absences` + `POST /coverage` | Owner frozen, caretaker partnership |

## Layer 5 — Frontend ↔ FastAPI (React dashboard)

| ID | Screen | Data source |
|---|---|---|
| F1 | Map markers | `GET /trees?bbox=…` via adapter |
| F2 | Tree detail + chart | `GET /trees/{id}`, `/readings` |
| F3 | Sensor panel | `GET /sensors` (1:1 tree) |
| F4 | Stats panel | `GET /stats/overview` mapped to cards |
| F5 | Stats page districts | `GET /stats/by-stadtteil` |
| F6 | Weather widget | `GET /weather/forecast` |
| F7 | No Supabase direct reads | Network tab shows only FastAPI + tiles |

## Layer 6 — Browser QA (`agent-browser`)

| ID | Action | Expected |
|---|---|---|
| B1 | Open `http://localhost:5173` | Map renders, no white screen |
| B2 | Stats drawer | Non-zero trees/sensors when seeded |
| B3 | Click tree marker | Detail panel opens |
| B4 | Navigate `/stats` | Charts render |
| B5 | Console | No CORS errors to `:8000` |

## Execution log

**Run:** 2026-06-27 (live DB) · Supabase connected · migrate + seed + demo complete

| Layer | Result | Notes |
|---|---|---|
| L1 Unit | **PASS** | calibration, lorawan, mapping, scoring |
| L2 API contract | **PASS** | 43 passed, 1 skipped |
| L3 DB/seed | **PASS** | 4,377 trees, 1,001 sensors, 302 users, demo Berta |
| L4 Demo spine | **PASS** | Berta adopted, tree_001 sensor, ingest 202 |
| L5 Frontend wiring | **PASS** | FastAPI adapter live on `:5173` |
| L6 Browser (API mode) | **PASS** | Map markers, stats show 4,377 trees / 302 users |

**Fixes applied:** URL-encode special chars in `DATABASE_URL` password; seed `auth.users` before `profiles`; Postgres NULL typing in tree profile lookup; HTTP ingest `fcnt` passthrough.

**Previous runs:** blocked without DB · mock-mode partial — see `docs/e2e-screenshots/continue-*`
