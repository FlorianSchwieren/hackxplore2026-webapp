# CLAUDE.md — Agent Operating Guide

> Read this first when working in this repo. It orients you fast and lists the rules you must not break. `AGENTS.md` is a symlink to this file.

## What this is
**Baumpate** — a hackathon backend (VEGA / HackXplore Karlsruhe challenge *"Smart Watering for Urban Trees"*). Citizens adopt urban trees, keep their soil healthy (gamified streaks), a cheap ESP32 + capacitive sensor reports moisture, and the city gets a transparency dashboard + (mocked) shortage prediction.

**We build the BACKEND only.** Frontends are built by others: a **Flutter** citizen app and a **React** city dashboard. Our job is the database, ingestion, business logic, aggregates, realtime, and seed/mock data.

## Read order
1. [`SPEC.md`](SPEC.md) — index, locked decisions, the 3‑minute demo spine.
2. [`docs/00-vision-and-value.md`](docs/00-vision-and-value.md) — the four value pillars + pitch narrative.
3. [`docs/01-architecture.md`](docs/01-architecture.md) — components, API boundary, data flows.
4. [`docs/02-data-model.md`](docs/02-data-model.md) — schema (source of truth for tables).
5. [`docs/03-api-contract.md`](docs/03-api-contract.md) — HTTP surface (source of truth for endpoints).
6. [`docs/04-sensor-and-lorawan.md`](docs/04-sensor-and-lorawan.md) — payloads, calibration, Helium adapter.
7. [`docs/05-scoring-and-gamification.md`](docs/05-scoring-and-gamification.md) — streak/score math, avatar states, edge cases.
8. [`docs/06-seeding-and-mock-data.md`](docs/06-seeding-and-mock-data.md) — seeds + species profiles + demo scenario.
9. [`docs/07-implementation-plan.md`](docs/07-implementation-plan.md) — phased build plan + repo layout.
10. [`docs/08-frontend-data-mapping.md`](docs/08-frontend-data-mapping.md) — serving the Flutter app's models.
11. [`docs/09-webapp-data-audit.md`](docs/09-webapp-data-audit.md) — serving the React reporting website (FastAPI‑only, we compute everything).

## Stack (locked)
Python 3.12 · **FastAPI** · **uv** · **SQLModel** · **Supabase** (Postgres + Realtime + Auth + RLS + PostGIS) · **Supabase SQL migrations** (not Alembic) · **Open‑Meteo** weather · **ngrok** for the demo · ML/prediction **mocked**.

## Invariants — do NOT violate
1. **Cooperative, never competitive.** Only `available` trees can be adopted. Adopted trees are joined **only** via owner **invitation** or by **covering a declared absence**. You can never take or out‑compete for a tree. (`POST /partnerships` must `409` on an adopted tree.)
2. **Backend only.** Don't build UI. Honour the contracts in `docs/03` so Flutter/React can develop in parallel.
3. **Sensor sends raw ADC**; the backend calibrates (`raw_to_pct`). Calibration is per‑sensor.
4. **Score = Σ per‑tree streaks** (not a flat counter). Each partnership has its own `streak`; forgetting a tree resets that tree's streak to 0. Verify against the worked example: 1000 → 909.
5. **Append‑only history.** Never update/delete `sensor_readings`, `weather_snapshots`, or `absences` — they're the future‑ML foundation.
6. **API boundary:** the **React website talks only to FastAPI** (the existing endpoints in [docs/03](docs/03-api-contract.md)) and **we do all computation** server‑side — it never touches Supabase directly. The **Flutter app** uses FastAPI for all reads/writes/logic, and may additionally subscribe to **Supabase Realtime only as a push channel** for rows FastAPI wrote. Supabase = datastore + realtime transport, never a place computation happens.
7. **Frontends are early/vibe-coded — they adapt to our clean API, not the reverse.** Don't mirror their invented types/column names or add endpoints just to satisfy their current code ([docs/09](docs/09-webapp-data-audit.md)). Provide the *necessary* data through clear, model-grounded endpoints. Sensor↔tree is **1:1** (each tree has its own sensor → per-tree state). No `age_years` (not in the data).
8. **The demo spine wins.** If a feature endangers the 7‑step demo (`SPEC.md` §4), cut or stub it. The realtime watering moment (steps 3–4) and city‑wide stats (step 6) must look flawless.
9. **All ~130k trees** live in `trees` for real citywide stats; **active fleet** (sensors/users/partnerships) is concentrated in `Innenstadt-Ost`/`Innenstadt-West` via the `stadtteil` field — no coordinate maths.

## Key facts & gotchas
- Tree PK is the source `objectid` → `trees.external_id`. **`lfdbnr` is often null** — never use it as an identifier.
- `artdeut`/`artlat` are ~72% filled citywide; `baumart_allgemein` is always present → species profiles key on the category with species overrides.
- Capacitive sensors read **lower raw when wetter** — calibration inverts (`dry > wet`). Calibration constants are **per‑probe and must be measured** (the sample values we saw were random test data — don't hardcode them). **Calibrate the demo probe in soil**, not water, else watered reads as `overwatered`.
- Defensive (light): **smooth + reject obvious outliers** before moving tree health, so a stray reading can't flip the avatar mid‑demo. ([docs/04](docs/04-sensor-and-lorawan.md) §3)
- The device sends `tree_id` (string, e.g. `tree_001`), not a `device_eui` → match on `sensors.device_ref`. It also sends device‑computed `moisture_percent/status/priority` — **ignore for health; recompute from `raw`** (store device values for reference).
- The geoportal API caps ~2,000 rows/request → **paginate** (`resultOffset`).
- Ingestion idempotency: unique `(sensor_id, fcnt)`; real device has no `fcnt` → fall back to `(sensor_id, measured_at)`.
- All timestamps UTC (`timestamptz`); the daily cron uses Europe/Berlin day boundaries.
- **Score** (= Σ per‑tree streaks) and **`streak_days`** (user‑level consecutive‑day flame) are **two different numbers** — the app needs both.
- **Liters can't come from a soil sensor** — `WaterRecord.liters`/`totalWaterLiters` only exist via user‑logged `watering_events`. Don't fabricate measured liters.
- App enums are narrower than ours: map `health_state` (5→4) and species (rich→5 + `other`) via [docs/08](docs/08-frontend-data-mapping.md); APIs return both forms.
- **Dropped/deferred** (don't build): **liters / `watering_events`** (sensor measures moisture, not volume → app shows the moisture curve via `GET /trees/{id}/readings`); **friends / leaderboard / `friendships`**; **user‑level `streak_days`**. `score` (= Σ per‑tree streaks) is the only gamification number.
- Edge case: heavy rain (`weather_snapshots`) must **not** penalize a streak (`overwatered` from rain isn't the user's fault).

## Working conventions
- Mirror `docs/02` for tables and `docs/03` for endpoints exactly; if you must deviate, **update the doc in the same change** (docs are the source of truth).
- Keep secrets in `.env` (never commit). The Supabase **service‑role key lives only in FastAPI**, never in a frontend.
- Seeds must be **idempotent**; mock generation uses a fixed random seed. `app/seed/demo.py` is authoritative — run it last.
- Prefer small, testable functions for `calibration.py`, `lorawan.py`, `services/scoring.py`; these have the unit tests that matter (`docs/07` §testing).

## Commands (once M0 exists)
- `make run` — start FastAPI (uvicorn).
- `make seed` / `python -m app.seed all` — seed everything (then `python -m app.seed demo`).
- `make test` — run tests.
- `make migrate` — apply Supabase SQL migrations.

## Status
Specification phase complete (this suite). Implementation starts at **M0** in [`docs/07`](docs/07-implementation-plan.md). No open product questions remain; open *technical* decisions are flagged inline in the docs (e.g. uncovered‑absence streak rule in `docs/05` §3.2 — default chosen).
