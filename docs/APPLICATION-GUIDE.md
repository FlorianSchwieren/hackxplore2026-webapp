# Baumpate — Complete Application Guide

> **Everything in one place:** product intent, architecture, every major module, database schema, API surface, frontend wiring, demo flows, configuration, and operational commands.  
> Companion for team handoff: [`TEAM-ONBOARDING.md`](TEAM-ONBOARDING.md) (setup checklist + secrets).

---

## Table of contents

1. [Product & demo spine](#1-product--demo-spine)
2. [Architecture & trust boundaries](#2-architecture--trust-boundaries)
3. [Repository map (every important path)](#3-repository-map)
4. [Configuration & environment](#4-configuration--environment)
5. [Database schema (Postgres + PostGIS)](#5-database-schema)
6. [Backend: request lifecycle](#6-backend-request-lifecycle)
7. [Sensor pipeline (calibration → health → streak)](#7-sensor-pipeline)
8. [LoRaWAN adapter (`app/lorawan.py`)](#8-lorawan-adapter)
9. [Scoring & gamification](#9-scoring--gamification)
10. [HTTP API reference](#10-http-api-reference)
11. [Authentication](#11-authentication)
12. [Seeding & demo data](#12-seeding--demo-data)
13. [Cron & background evaluation](#13-cron--background-evaluation)
14. [React dashboard (hackxplore2026-webapp)](#14-react-dashboard)
15. [Flutter app integration (external)](#15-flutter-app-integration)
16. [ESP32 / hardware integration](#16-esp32--hardware-integration)
17. [Realtime (Supabase)](#17-realtime-supabase)
18. [Testing strategy](#18-testing-strategy)
19. [Deployment & demo day](#19-deployment--demo-day)
20. [Invariants, deferred features, gotchas](#20-invariants-deferred-gotchas)
21. [Current database snapshot](#21-current-database-snapshot)
22. [Command reference](#22-command-reference)

---

## 1. Product & demo spine

**Baumpate** (*Baumpatenschaft* — urban tree sponsorship) is a civic platform where:

- Citizens **adopt** urban trees and keep soil moisture in a species-specific healthy band.
- A cheap **capacitive sensor** (ESP32) reports **raw ADC** values; the backend calibrates to moisture %.
- Gamification: each tree partnership has a **streak**; user **score = sum of streaks** across their trees.
- The **city dashboard** shows fleet health, participation, and (mocked) shortage prediction.

### 3-minute demo (must always work)

| Step | Actor | What happens |
|------|-------|----------------|
| 1 | User 1 | Push notification: tree thirsty (Flutter — may be mocked) |
| 2 | User 1 | Opens app → sad avatar (Berta, low moisture) |
| 3 | User 1 | **Physically waters** real tree; ESP32 POSTs raw reading |
| 4 | Backend | Detects healthy transition → streak +1 → Realtime → happy avatar |
| 5 | User 1 | Declares **absence** (streak frozen) |
| 6 | City | **React dashboard** — city stats, health mix, sensors |
| 7 | User 2 | Covers absence → earns score by **helping** (never competing) |

**Demo entities:**

| Entity | Value |
|--------|-------|
| Demo tree | **Berta** (`name='Berta'`, adopted) |
| Real sensor | `device_ref = tree_001`, `is_real = true` |
| Demo users | Alex (`alex@baumpate.demo`), Sam (`sam@baumpate.demo`) |
| Starting moisture | ~22% (thirsty) after `seed demo` or `make_thirsty.py` |

Reset before pitch: `python -m app.seed demo`

---

## 2. Architecture & trust boundaries

```
                    ┌─────────────────────────────────────┐
                    │     Supabase (managed cloud)         │
                    │  Postgres + PostGIS + Auth + Realtime│
                    └──────────────▲───────────▲──────────┘
                                   │           │
                        service    │           │ Realtime WS
                        role writes│           │ (Flutter only)
                                   │           │
┌──────────┐  POST raw   ┌─────────┴───────────┴─────────┐
│  ESP32   │────────────►│      FastAPI :8000             │
└──────────┘             │  ingest · routers · services   │
                         └─────────▲───────────────────────┘
                                   │ REST JSON
              ┌────────────────────┼────────────────────┐
              │                    │                    │
       ┌──────┴──────┐      ┌──────┴──────┐             │
       │ React :5173 │      │ Flutter app│             │
       │ FastAPI ONLY│      │ REST + RT  │             │
       └─────────────┘      └────────────┘             │
```

### Who may do what

| Client | Reads | Writes | Realtime |
|--------|-------|--------|----------|
| **ESP32** | — | `POST /ingest/http` | — |
| **React dashboard** | All via FastAPI | — (read-only UI) | — |
| **Flutter app** | FastAPI | FastAPI (partnerships, absences, me) | Supabase subscribe |
| **FastAPI** | SQLModel/raw SQL | Everything in DB (service role) | publishes via DB writes |
| **Supabase Auth** | — | issues JWT | — |

**Golden rules:**

1. **Computation never happens in Supabase functions or frontends** — only in FastAPI.
2. **Cooperative, never competitive** — only `available` trees can be adopted; 409 on taken trees.
3. **Append-only history** — never UPDATE/DELETE `sensor_readings`, `weather_snapshots`, `absences`.
4. **Sensor sends raw ADC** — ignore device-computed moisture for health.
5. **Score = Σ per-tree streaks** (not a flat counter; not user-level `streak_days`).

---

## 3. Repository map

```
HackXPlore/                              ← git monorepo root
│
├── SPEC.md                              ← product index, demo spine, locked decisions
├── CLAUDE.md / AGENTS.md                ← agent operating rules (symlink)
├── docs/
│   ├── 00–09                            ← specification suite (source of truth)
│   ├── TEAM-ONBOARDING.md               ← setup + secrets handoff
│   └── APPLICATION-GUIDE.md             ← this file
│
├── app/                                 ← Python FastAPI backend
│   ├── main.py                          ← mounts /api/v1 sub-app, CORS, 503 on missing DB
│   ├── config.py                        ← pydantic-settings from .env
│   ├── db.py                            ← engine, get_session(), apply-sql migrations
│   ├── auth.py                          ← JWT + ingest secret + DEV_AUTH_DISABLED
│   ├── models.py                        ← SQLModel tables (mirror docs/02)
│   ├── schemas.py                       ← Pydantic request/response (mirror docs/03)
│   ├── calibration.py                   ← raw↔pct, health_score, health_state, outliers
│   ├── lorawan.py                       ← Helium-style encode/decode
│   ├── mapping.py                       ← backend enums → Flutter-friendly fields
│   ├── cron.py                          ← daily scoring entrypoint
│   ├── routers/
│   │   ├── ingest.py                    ← /ingest/http, /ingest/lorawan
│   │   ├── trees.py                     ← map bbox, detail, readings, rename
│   │   ├── partnerships.py              ← adopt, invite, leave
│   │   ├── absences.py                  ← absence + coverage pool
│   │   ├── me.py                        ← profile, my trees, notifications
│   │   ├── stats.py                     ← overview, stadtteil, sensors list
│   │   ├── weather.py                   ← Open-Meteo proxy
│   │   └── predictions.py               ← mocked ML stub
│   ├── services/
│   │   ├── ingestion.py                 ← core sensor → DB pipeline
│   │   ├── scoring.py                   ← streak math, daily cron, immediate award
│   │   └── weather.py                   ← fetch + cache weather_snapshots
│   └── seed/
│       ├── __main__.py                  ← CLI: python -m app.seed all|demo|…
│       ├── species.py                   ← moisture profiles
│       ├── trees.py                     ← GeoJSON or geoportal paginated
│       ├── sensors.py                   ← ~1000 mock fleet + calibration
│       ├── readings.py                  ← one snapshot per mock sensor
│       ├── users.py                     ← auth.users + profiles
│       ├── partnerships.py              ← owners, streaks, absences
│       └── demo.py                      ← Berta + tree_001 (authoritative)
│
├── supabase/migrations/
│   ├── 0001_init.sql                    ← tables, indexes, append-only triggers, realtime pub
│   └── 0002_rls.sql                     ← RLS for Flutter Realtime reads
│
├── tests/                               ← pytest (unit + API + spine)
├── scripts/                             ← fake_water, make_thirsty, mock_stream, e2e_validate
├── data/raw/karlsruhe_trees_citycenter.geojson
│
└── hackxplore2026-webapp/               ← React city dashboard
    └── src/
        ├── App.tsx                      ← routes: /, /stats
        ├── pages/MainPage.tsx, StatsPage.tsx
        ├── components/Map/              ← MapView, markers, SearchBar, filters
        ├── components/Dashboard/        ← StatsPanel, WeatherWidget
        ├── components/Detail/           ← TreeDetailPanel, SensorDetailPanel, HumidityChart
        ├── lib/api/client.ts           ← apiFetch → VITE_API_BASE_URL
        ├── lib/api/mappers.ts          ← API JSON → UI types
        ├── lib/queries/                ← React Query hooks
        └── lib/mock/                   ← fallback when VITE_USE_MOCK_DATA=true
```

---

## 4. Configuration & environment

### Backend `.env` (repo root)

| Variable | Purpose |
|----------|---------|
| `API_PREFIX` | Default `/api/v1` |
| `DEV_AUTH_DISABLED` | `true` → fixed dev user UUID, skip JWT |
| `DATABASE_URL` | Postgres session pooler URI |
| `SUPABASE_URL` | Project URL |
| `SUPABASE_PUBLISHABLE_KEY` / `SUPABASE_ANON_KEY` | Alias accepted |
| `SUPABASE_SECRET_KEY` / `SUPABASE_SERVICE_ROLE_KEY` | Backend only; bypasses RLS |
| `SUPABASE_JWKS_URL` | JWT verify (preferred over HS256 secret) |
| `INGEST_SHARED_SECRET` | Bearer token for `/ingest/*` |
| `OPEN_METEO_BASE_URL`, `KARLSRUHE_LAT/LON` | Weather |
| `OUTLIER_RAW_MARGIN` | Reject raw values outside calibration ± margin |
| `SMOOTHING_WINDOW` | Median window for health (default 5) |
| `STATE_DEBOUNCE_READINGS` | Consecutive smoothed states before flip |
| `INGEST_DEDUPE_WINDOW_SECONDS` | Idempotency window when no fcnt |
| `THRIVING_STREAK_THRESHOLD` | Days for `thriving` vs `healthy` |
| `RAIN_PENALTY_SKIP_PRECIP_MM_24H` | Don't break streak on rain overwater |
| `UNCOVERED_ABSENCE_PROTECTS_STREAK` | Documented edge case flag |

**Password in `DATABASE_URL`:** URL-encode special characters (`!` → `%21`).

### Frontend `hackxplore2026-webapp/.env`

| Variable | Purpose |
|----------|---------|
| `VITE_USE_MOCK_DATA` | `false` = live FastAPI |
| `VITE_API_BASE_URL` | e.g. `http://localhost:8000/api/v1` |
| `VITE_SUPABASE_URL/ANON_KEY` | Optional; live dashboard uses FastAPI only |
| `VITE_STADIA_API_KEY` | Map tiles; empty → OpenFreeMap fallback |

---

## 5. Database schema

### Entity relationship (conceptual)

```
species_water_profiles ──► trees ◄──► sensors (1:1)
                              │
                              ├── sensor_readings (append-only)
                              ├── tree_partnerships ──► profiles
                              └── absences ──► tree_partnerships

weather_snapshots (append-only)     notifications
profiles ◄── FK ── auth.users (Supabase)
```

### Table: `profiles`

App user extending Supabase Auth.

| Column | Notes |
|--------|-------|
| `id` | UUID = `auth.users.id` |
| `display_name`, `email`, `avatar_url` | |
| `score` | Cached **Σ streaks** across active partnerships |
| `notify_help_opt_in` | Caretaker pool notifications |

### Table: `species_water_profiles`

Moisture bands per species category or Latin prefix.

| Column | Notes |
|--------|-------|
| `match_kind` | `category` or `species_lat` |
| `match_value` | e.g. `Laubbaum`, `Tilia cordata`, `demo_berta` |
| `optimal_min/max_pct`, `dry_critical_pct`, `wet_critical_pct` | Health bands |
| `priority` | Higher wins when multiple match |

### Table: `trees`

~130k target citywide; currently ~4.4k inner city seeded.

| Column | Notes |
|--------|-------|
| `external_id` | Karlsruhe geoportal `objectid` (PK source) |
| `geom` | PostGIS `POINT(4326)` |
| `stadtteil` | District filter (no coordinate maths for demo fleet) |
| `status` | `available` \| `adopted` |
| `moisture_pct`, `health_score`, `health_state` | **Denormalized cache** updated on ingest |
| `species_profile_id` | Resolved at seed time |

**Never use `lfdbnr` as identifier** — often null.

### Table: `sensors`

Strict **1:1** with trees.

| Column | Notes |
|--------|-------|
| `device_ref` | Ingest lookup key (e.g. `tree_001`, `MOCK-00001`) |
| `device_eui` | LoRaWAN identity |
| `calibration_dry`, `calibration_wet` | Per-probe ADC endpoints (**dry > wet** for capacitive) |
| `is_real` | One true probe for demo |
| `status` | `working` \| `inactive` \| `defect` |

### Table: `sensor_readings`

**Append-only** (trigger blocks UPDATE/DELETE).

| Column | Notes |
|--------|-------|
| `raw` | Source of truth from device |
| `moisture_pct` | Backend-calibrated |
| `fcnt` | LoRaWAN frame counter; idempotency |
| `is_outlier` | Stored but excluded from smoothing |
| `source` | `lorawan` \| `mock` \| `manual` |
| `device_*` | Device-computed values stored for reference only |

**Unique indexes:**

- `(sensor_id, fcnt)` WHERE `fcnt IS NOT NULL`
- `(sensor_id, measured_at)` WHERE `fcnt IS NULL`

### Table: `tree_partnerships`

| Column | Notes |
|--------|-------|
| `role` | `owner` \| `member` \| `caretaker` |
| `active_from`, `active_to` | Caretaker has bounded `active_to` |
| `streak` | Per-tree consecutive healthy days |
| `streak_frozen` | True during declared absence |
| `last_eval_date` | Prevents double-count (cron + immediate) |

**Unique:** one active owner per tree; one active user per tree.

### Table: `absences`

**Append-only.**

| Column | Notes |
|--------|-------|
| `status` | `open` \| `covered` \| `expired` |
| `covering_partnership_id` | Set when someone covers |

### Table: `weather_snapshots`

Append-only cache of Open-Meteo responses + `forecast_json` JSONB.

### Table: `notifications`

In-app notifications (stub data possible from seeds).

### RLS (`0002_rls.sql`)

- Authenticated users may **SELECT** public tree/sensor/reading data (for Realtime).
- Users see own profile, partnerships, notifications.
- **No client writes** — FastAPI uses service role.

### Realtime publication

Tables added to `supabase_realtime`: `trees`, `tree_partnerships`, `sensor_readings`.

---

## 6. Backend: request lifecycle

```
HTTP Request
    → FastAPI router (app/routers/*.py)
    → Depends(require_user) or require_ingest_secret
    → Depends(get_session) → SQLModel Session
    → Raw SQL (text()) or SQLModel ORM
    → services/* for business logic
    → session.commit()
    → Pydantic response (schemas.py)
```

**Two FastAPI apps** in `main.py`:

- Root `app` — `/healthz`, `/docs` (health only on root docs)
- Mounted `api` at `API_PREFIX` — all business routes + **use `/api/v1/docs`**

Missing `DATABASE_URL` → **503** with clear message (not opaque 500).

---

## 7. Sensor pipeline

Full path for demo steps 3–4:

```
ESP32 POST /ingest/http
  → ingest.py: encode_uplink(payload) → decode_uplink(envelope)
  → ingestion.ingest_decoded_reading()
      1. Lookup sensor by device_ref (= tree_id string)
      2. Load tree + species_water_profiles
      3. Validate calibration_dry ≠ calibration_wet
      4. Dedupe (_find_duplicate by fcnt or time window)
      5. raw_to_pct(raw, dry, wet)
      6. is_outlier_raw? → store reading, skip health update if outlier
      7. Median of last SMOOTHING_WINDOW non-outlier readings
      8. health_state(smoothed, profile, streak, THRIVING_THRESHOLD)
      9. _debounced_state — need N consecutive candidate states
     10. Update trees.moisture_pct, health_score, health_state, last_reading_at
     11. If crossed into healthy band → award_immediate_if_needed()
     12. INSERT sensor_readings (append-only), UPDATE sensors.last_seen_at
     13. COMMIT → Supabase Realtime pushes to Flutter
```

### Calibration (`app/calibration.py`)

Capacitive: **lower raw = wetter**. Linear map:

```
pct = (dry - raw) / (dry - wet) * 100   clamped [0, 100]
```

**Health states** (backend, 5 buckets):

| State | Condition |
|-------|-----------|
| `critical` | m < dry_critical |
| `thirsty` | dry_critical ≤ m < optimal_min |
| `healthy` | optimal_min ≤ m ≤ optimal_max (streak < threshold) |
| `thriving` | in band + streak ≥ THRIVING_STREAK_THRESHOLD |
| `overwatered` | m > wet_critical |

**health_score** 0–100: 80–100 in optimal band; ramps down toward dry/wet critical.

### Defensive ingest (docs/04)

- **Outlier rejection:** raw outside `[min(d,w)-margin, max(d,w)+margin]`
- **Smoothing:** median of last N valid readings
- **Debounce:** health_state only changes after N consecutive smoothed candidates agree
- Prevents single stray reading from flipping avatar mid-demo

---

## 8. LoRaWAN adapter

`app/lorawan.py` simulates Helium/ChirpStack webhook format so HTTP and LoRaWAN share one decoder.

### Binary payload layout (6+ bytes)

| Bytes | Content |
|-------|---------|
| 0–1 | raw ADC (big-endian uint16) |
| 2–3 | battery_mv (big-endian uint16) |
| 4 | firmware version |
| 5 | flags |

### encode_uplink (HTTP → envelope)

Input: `{ tree_id, raw_value, battery_*, rssi, created_at, fcnt, … }`  
Output: `{ deviceInfo.devEui: "BAUMPATE-{tree_id}", fCnt, data: base64, rxInfo, time }`

### decode_uplink (envelope → dict)

Output: `{ device_ref, raw, fcnt, rssi, snr, battery_mv, measured_at, device_* }`

`device_ref` = `devEui` with `BAUMPATE-` prefix stripped.

---

## 9. Scoring & gamification

### Core model

- **`tree_partnerships.streak`** — consecutive days tree was in healthy band `[optimal_min, optimal_max]`
- **`profiles.score`** = SUM of streaks over user's active partnerships
- Forgetting a tree → that tree's streak → **0** (expensive!)
- Worked example: 10 trees × streak 100 = 1000; forget one → 9×101 + 0 = **909**

### Daily cron (`app/cron.py` → `scoring.evaluate_daily`)

Runs for Europe/Berlin `today`:

```
for each active partnership not yet evaluated today:
  if streak_frozen: skip
  elif tree in healthy band: streak += 1
  else: streak = 0
  unless heavy rain + over optimal_max → don't penalize (rain carve-out)
  last_eval_date = today
recompute affected users' score
```

Also: `expire_coverage()` — expire absences, unfreeze owner streaks.

### Immediate award (demo path)

On ingest, when moisture **transitions into healthy band**:

```python
award_immediate_if_needed(tree_id, new_healthy and not old_healthy)
  → owner partnership streak += 1
  → last_eval_date = today  # cron won't double-count
  → recompute_user_score
```

### Cooperative mechanics

| Action | Endpoint | Rule |
|--------|----------|------|
| Adopt | `POST /partnerships` | Only if `status=available`; else **409** |
| Invite member | `POST /partnerships/{id}/invite` | Owner only; cooperative co-tending |
| Leave | `DELETE /partnerships/{id}` | If last partner leaves → tree `available` |
| Declare absence | `POST /absences` | Freezes owner streak; absence `open` |
| Cover | `POST /coverage` | Creates `caretaker` partnership; absence `covered` |
| Cover own absence | — | **400** blocked |

---

## 10. HTTP API reference

Base: `/api/v1` · Full contract: [`docs/03-api-contract.md`](03-api-contract.md) · Interactive: `/api/v1/docs`

### Health

| Method | Path | Auth | Response |
|--------|------|------|----------|
| GET | `/healthz` | — | `{ status, time }` |

### Ingestion

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| POST | `/ingest/http` | Ingest secret | ESP32 shape; wraps → decodes |
| POST | `/ingest/lorawan` | Ingest secret | Raw Helium envelope |

Response: `{ accepted, reading_id, moisture_pct, health_state, streak_awarded, is_outlier }`

### Trees

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET | `/trees?bbox=…` | User | PostGIS envelope; filters: status, health, monitored, stadtteil |
| GET | `/trees/available?bbox=…` | User | status=available only |
| GET | `/trees/{id}` | User | Detail + sensor + partners + recent readings |
| GET | `/trees/{id}/readings?days=30` | User | Time series for charts |
| PATCH | `/trees/{id}/name` | User | Partner only; rename tree |

**bbox format:** `minLon,minLat,maxLon,maxLat` (WGS84)  
**Karlsruhe dashboard bbox:** `8.35,48.98,8.45,49.03`

Response includes Flutter mapping fields: `title`, `species_app`, `health_state_app`, `coordinates`.

### Partnerships

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| POST | `/partnerships` | User | Adopt `{ tree_id }` → 201 or 409 |
| POST | `/partnerships/{id}/invite` | User | `{ email }` → member |
| DELETE | `/partnerships/{id}` | User | Leave → 204 |

**Co-partners:** there is no `friendships` table. Users who tend the same tree are linked via `tree_partnerships`. Use `GET /me/co-partners` for a deduplicated list of other profiles sharing at least one active partnership (owner, member, or caretaker). Per-tree partners are also on `GET /trees/{id}` → `partners[]`.

### Absences & coverage

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| POST | `/absences` | User | `{ tree_id, from_date, to_date }` |
| GET | `/coverage/open?bbox=…` | User | Trees needing caretaker |
| POST | `/coverage` | User | `{ absence_id }` |

### User / me

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET | `/me` | User | Profile + score + tree count |
| PATCH | `/me` | User | display_name, notify_help_opt_in |
| GET | `/me/trees` | User | Homepage map: trees + per-tree streak |
| GET | `/me/co-partners` | User | Users sharing ≥1 active tree partnership |
| GET | `/notifications` | User | List |
| PATCH | `/notifications/{id}` | User | Mark read |

### Dashboard / stats

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET | `/stats/overview` | User | City totals, health distribution, sensor counts |
| GET | `/stats/by-stadtteil` | User | Per-district aggregates |
| GET | `/sensors?status=` | User | Maintenance map (up to 5000) |

### Weather & predictions

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET | `/weather/forecast` | User | Open-Meteo; caches snapshot |
| GET | `/predictions?bbox=&horizon_days=` | — | **Mock** risk scores |

---

## 11. Authentication

### User JWT (`app/auth.py`)

1. Extract `Authorization: Bearer <token>`
2. Verify via `SUPABASE_JWKS_URL` (RS256/ES256) **or** `SUPABASE_JWT_SECRET` (HS256)
3. `sub` claim → `CurrentUser.id`

**Dev bypass:** `DEV_AUTH_DISABLED=true` → all user routes run as the **team demo profile** (`Taylor Team`, `team@baumpate.demo`). Seed it with `uv run python -m app.seed team_demo` (included in `make seed`). Override with `DEV_AUTH_USER_ID=<uuid>` if needed.

### Ingest secret

`Authorization: Bearer <INGEST_SHARED_SECRET>` — compared literally in `require_ingest_secret`.

### RLS vs service role

FastAPI connects with `DATABASE_URL` (direct Postgres, full access). Flutter Realtime uses anon key + RLS-scoped SELECT.

---

## 12. Seeding & demo data

### Order (`python -m app.seed all`)

```
species → trees → sensors → readings → users → partnerships → demo
```

All seeds are **idempotent** (upserts); random seed **42** for reproducibility.

| Module | What it creates |
|--------|-----------------|
| `species.py` | Category defaults + ~12 species_lat overrides + demo_berta |
| `trees.py` | Local GeoJSON (4377) OR `--citywide` geoportal paginate (~130k) |
| `sensors.py` | ~1000 inner-city trees get mock sensors; calibration 3099/1500 |
| `readings.py` | One snapshot per sensor; believable health distribution |
| `users.py` | Inserts `auth.users` then `profiles` (Alex, Sam, 300 fakes) |
| `partnerships.py` | Owners, members, streaks, fake absences |
| `demo.py` | **Authoritative** — Berta, tree_001, thirsty start, Alex streak 12 |

### Demo seed details (`demo.py`)

- Picks/prepares Berta tree (prefers `Tilia` in Innenstadt)
- Sensor `tree_001`, `is_real=true`, calibration 3099/1500
- Alex owner, streak 12; Sam gets 2 nearby trees
- Starting reading: moisture **22%** → `thirsty`
- Recomputes Alex + Sam scores

---

## 13. Cron & background evaluation

```bash
uv run python -m app.cron
# or
uv run python -c "from app.cron import run_daily; print(run_daily())"
```

Returns: `{ expired_coverages, evaluated_partnerships }`

Schedule in production: Supabase cron or external scheduler at ~20:00 Europe/Berlin.

---

## 14. React dashboard

### Routes (`App.tsx`)

| Path | Page |
|------|------|
| `/` | MainPage — map + stats drawer |
| `/stats` | StatsPage — full analytics |

### Data flow

```
Component → useXxx hook (React Query)
  → if VITE_USE_MOCK_DATA: lib/mock/*
  → else: apiFetch('/endpoint') in lib/api/client.ts
  → mappers.ts transforms API → UI types (Tree, Sensor, NetworkStats, …)
  → component renders
```

**Stale time:** 5 minutes default; refetch on window focus disabled.

### Hook → endpoint map

| Hook | Endpoint |
|------|----------|
| `useTrees` | `GET /trees?bbox=…&limit=2000` |
| `useTreeDetail` | `GET /trees/{id}` |
| `useSensors` | `GET /sensors` |
| `useTreeReadings` / `useSensorReadings` | `GET /trees/{id}/readings` |
| `useNetworkStats` | `GET /stats/overview` |
| `useStadtteilStats` | `GET /stats/by-stadtteil` |
| `useWeatherQuery` | `GET /weather/forecast` |
| `useLeaderboard` | Returns `[]` in live mode (deferred) |

### Health mapping (API → UI)

Backend `health_state` → UI `humidity_status`:

| Backend | UI |
|---------|-----|
| critical | dry |
| thirsty | low |
| healthy, thriving | normal |
| overwatered | moist |

### Components wired to live API

- `MapView` — trees + sensors clustered on MapLibre
- `StatsPanel` — drawer overview
- `StatsPage` — charts (some history is single-point stub from overview)
- `TreeDetailPanel`, `SensorDetailPanel` — detail + humidity chart
- `WeatherWidget` — live forecast
- `SearchBar` — trees/sensors from API; **district list still static mock**

### Mock mode

`VITE_USE_MOCK_DATA=true` — no backend required; uses `src/lib/mock/*`.

---

## 15. Flutter app integration

Not in this repo; contract:

- **All reads/writes/logic** → FastAPI endpoints above
- **Realtime** → subscribe to `trees`, `tree_partnerships`, `sensor_readings` changes
- **Enum mapping** → [`docs/08-frontend-data-mapping.md`](08-frontend-data-mapping.md)
  - 5 health states → 4 app states via `health_state_app`
  - Species → `species_app` (oak, maple, birch, pine, willow, other)

---

## 16. ESP32 / hardware integration

**Never connect ESP32 to Supabase directly.**

```
POST {API_HOST}/api/v1/ingest/http
Authorization: Bearer {INGEST_SHARED_SECRET}
Content-Type: application/json

{
  "tree_id": "tree_001",
  "raw_value": 2480,
  "battery_voltage": null,
  "rssi": -47,
  "created_at": "2026-06-27T14:03:00Z",
  "fcnt": 12345
}
```

- Match sensor: `sensors.device_ref = tree_id`
- Calibrate probe **in soil**, not water (else watered reads overwatered)
- Demo scripts: `scripts/fake_water.py`, `scripts/make_thirsty.py`

---

## 17. Realtime (Supabase)

Flutter subscribes (example channels):

- `trees` UPDATE — moisture/health changes
- `tree_partnerships` UPDATE — streak changes
- `sensor_readings` INSERT — new readings

React dashboard **does not** use Realtime — it refetches via React Query.

Flow: FastAPI COMMIT → Postgres logical replication → Supabase Realtime → WebSocket → app UI update.

---

## 18. Testing strategy

```bash
make test                    # full pytest
uv run pytest tests/test_calibration.py -v   # pure math
uv run pytest tests/test_lorawan.py -v     # encode/decode roundtrip
uv run pytest tests/test_scoring.py -v     # 1000→909 example
uv run pytest tests/test_e2e_spine.py -v   # needs DATABASE_URL + seed
```

| File | Covers |
|------|--------|
| `test_calibration.py` | raw_to_pct, health_state, outliers |
| `test_lorawan.py` | binary payload roundtrip |
| `test_mapping.py` | species/health app mapping |
| `test_scoring.py` | daily_streak_next, score sum |
| `test_api_integration.py` | HTTP contract (mocked DB optional) |
| `test_e2e_spine.py` | Berta, tree_001, ingest, stats |

Layered E2E plan: [`docs/e2e-validation-plan.md`](e2e-validation-plan.md)

---

## 19. Deployment & demo day

### Local (development)

```bash
make run                              # :8000
cd hackxplore2026-webapp && npm run dev   # :5173
```

### Demo day (typical)

1. Supabase cloud project (EU region)
2. FastAPI on laptop + **ngrok** `ngrok http 8000`
3. ESP32 POSTs to ngrok URL
4. Flutter/React point to ngrok `/api/v1`
5. Run `python -m app.seed demo` immediately before pitch

### Frontend deploy

`hackxplore2026-webapp/netlify.toml` + GitHub Actions deploy workflow.  
Set `VITE_API_BASE_URL` to production API URL in CI env.

---

## 20. Invariants, deferred, gotchas

### Must not violate

1. Cooperative adoption only
2. Raw ADC → backend calibrates
3. Score = Σ streaks
4. Append-only history tables
5. React → FastAPI only
6. Demo spine priority

### Deferred / not built

- User-level `streak_days` (separate flame counter)
- `watering_events` / liters (sensor can't measure volume)
- `friendships` table, global friends graph, leaderboard (co-partners on shared trees: `GET /me/co-partners`)
- Real ML predictions (stub only)
- Full leaderboard in React live mode

### Gotchas

| Topic | Detail |
|-------|--------|
| Tree PK | `external_id` from geoportal `objectid` |
| `lfdbnr` | Often null — don't use |
| Capacitive calibration | dry > wet; calibrate in soil |
| DATABASE_URL passwords | URL-encode special chars |
| `received_at` | Must be set on insert (ORM doesn't always pick PG default) |
| Citywide vs demo fleet | All trees in DB for stats; sensors/users only inner city |
| Git secrets | Never commit Supabase keys — push protection will block |

---

## 21. Current database snapshot

After `make seed` + `demo` (typical dev env):

| Table | ~Count |
|-------|--------|
| trees | 4,377 (Innenstadt-Ost + West) |
| sensors | 1,001 (1 real: tree_001) |
| sensor_readings | ~970+ |
| profiles | 302 |
| tree_partnerships | ~588 active |
| absences | ~8 open |
| species_water_profiles | 20 |

**Berta:** adopted, demo sensor, health varies after ingest/tests.  
**Not yet seeded:** full ~130k citywide (`python -m app.seed trees --citywide`).

---

## 22. Command reference

### Backend

```bash
cp .env.example .env && uv sync --extra dev
make migrate && make seed && python -m app.seed demo
make run | make test | make lint
uv run python scripts/fake_water.py --raw 1900
uv run python scripts/make_thirsty.py
uv run python -m app.cron
python scripts/e2e_validate.py --with-db
```

### Frontend

```bash
cd hackxplore2026-webapp && cp .env.example .env
npm install && npm run dev && npm run typecheck
```

### URLs

| Resource | URL |
|----------|-----|
| Map | http://localhost:5173/ |
| Stats | http://localhost:5173/stats |
| API Swagger | http://localhost:8000/api/v1/docs |
| Health | http://localhost:8000/healthz |

---

## Appendix A — Documentation index

| Doc | Content |
|-----|---------|
| `SPEC.md` | Index + locked decisions |
| `docs/00-vision-and-value.md` | Pitch narrative |
| `docs/01-architecture.md` | Components + data flows |
| `docs/02-data-model.md` | Schema source of truth |
| `docs/03-api-contract.md` | HTTP surface source of truth |
| `docs/04-sensor-and-lorawan.md` | Payloads, calibration, smoothing |
| `docs/05-scoring-and-gamification.md` | Streak math, absence rules |
| `docs/06-seeding-and-mock-data.md` | Seed order, species values |
| `docs/07-implementation-plan.md` | Milestones M0–M9 |
| `docs/08-frontend-data-mapping.md` | Flutter enum mapping |
| `docs/09-webapp-data-audit.md` | React ↔ FastAPI audit |
| `docs/TEAM-ONBOARDING.md` | Setup + secrets handoff |
| `docs/e2e-validation-plan.md` | QA layers |

---

## Appendix B — Worked trace: watering Berta

1. **State before:** Berta `moisture_pct≈22`, `health_state=thirsty`, Alex `streak=12`
2. **POST** `/ingest/http` `{ tree_id: "tree_001", raw_value: 1900 }`
3. **Lookup** sensor calibration 3099/1500 → pct ≈ 75%
4. **Smooth** median over recent readings
5. **State** → `healthy` or `thriving` (demo profile band 40–88)
6. **Transition** not-healthy → healthy → `award_immediate_if_needed` → streak 13
7. **DB** new row in `sensor_readings`; `trees` updated; `profiles.score` recomputed
8. **Flutter** Realtime push → avatar animation
9. **React** refresh/refetch → map marker color updates via `humidity_status`

---

*End of application guide. For secrets and clone setup, see [`TEAM-ONBOARDING.md`](TEAM-ONBOARDING.md).*
