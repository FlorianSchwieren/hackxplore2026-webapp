# 01 — Architecture

> How the pieces fit, who owns which responsibility, the exact data flows behind the demo, and how we deploy it on demo day.

## 1. Components

```
┌────────────────────────────────────────────────────────────────────────┐
│                              FRONTENDS (not ours)                        │
│  Flutter app (citizens)                React dashboard (city)            │
│   • reads + realtime ↘                  • aggregates ↘                    │
│   • writes via REST ↘  ↘                • map reads ↘ ↘                   │
└───────────────────────┼──┼───────────────────────────┼──┼───────────────┘
                        │  │                           │  │
            REST (writes/logic)              REST (aggregates) │ direct reads
                        │  └──────────────┐                │  │ (PostGIS/RLS)
                        ▼                 │                ▼  │
┌──────────────────────────────┐         │   ┌───────────────┴──────────────┐
│        FastAPI service        │        │   │          Supabase            │
│  • /ingest/http, /ingest/lora │  service-role  │  • Postgres (+PostGIS)   │
│  • partnerships, absences     │◄──key──►│   │  • Realtime (websockets)     │
│  • scoring (cron)             │        │   │  • Auth (email/password)     │
│  • /stats/*, /weather, /pred  │        │   │  • Row Level Security (RLS)  │
└───────────────┬──────────────┘         │   └──────────────────────────────┘
                │                         │
        HTTP POST (raw ADC)         Open-Meteo (weather)
                │
        ┌───────┴────────┐
        │  ESP32 sensor  │  (1 real device; the rest are mocked rows)
        └────────────────┘
```

> The diagram shows the general shape; per the boundary in §3, the **website talks to FastAPI only** (no direct Supabase), and the app's *only* direct Supabase use is the **Realtime** subscription.

## 2. Responsibility split

### Supabase owns
- **Persistence** — all tables (see [docs/02](02-data-model.md)).
- **Realtime** — the Flutter app subscribes to changes on `sensor_readings` / `trees` / `tree_partnerships` and updates instantly (the demo's step‑4 moment).
- **Auth** — simple email/password; issues JWTs the app/dashboard send on requests.
- **RLS** — scopes what the app's **Realtime subscription** may receive (the app's only direct Supabase use; anon/auth key).
- **PostGIS** — spatial column + bbox/viewport queries so the map never loads 130k points at once.

### FastAPI owns (the "logic wrapper")
- **Ingestion + LoRaWAN adapter** — `/ingest/http` (raw sensor) → wrap into a Helium‑style uplink → `/ingest/lorawan` (decoder) → store reading, recompute health, maybe award streak. ([docs/04](04-sensor-and-lorawan.md))
- **Business logic with rules** — adoption, invitations, absences, coverage (enforces the *no‑competition* invariant). ([docs/03](03-api-contract.md))
- **Scoring** — daily cron evaluation + the demo's immediate‑award path. ([docs/05](05-scoring-and-gamification.md))
- **Aggregates** — `/stats/*` for the dashboard.
- **Weather** — proxy + cache Open‑Meteo; write `weather_snapshots` for history.
- **Prediction stub** — `/predictions` returning plausible mock data on the real contract.
- Uses the Supabase **service‑role key** → bypasses RLS for trusted server‑side writes.

## 3. The API boundary (hybrid — locked decision A)

| Operation | Goes through | Why |
|---|---|---|
| App: live tree/sensor updates | **Supabase Realtime (direct)** | Instant push without us building websocket infra |
| App: read my trees, map tiles | **FastAPI** | computed reads (health/score); PostGIS bbox server‑side |
| App: adopt / invite / declare absence / cover | **FastAPI** | Needs rule enforcement |
| App/Sensor: ingest reading | **FastAPI** | LoRaWAN adapter + health recompute |
| **Dashboard: everything** (trees, sensors, readings, stats, leaderboard, weather) | **FastAPI only** | website never touches Supabase directly; **all computation server‑side** ([docs/09](09-webapp-data-audit.md)) |

**Rule of thumb:** *the React website talks only to FastAPI. The Flutter app talks to FastAPI for all reads/writes/logic, and may additionally subscribe to Supabase Realtime purely as a push channel for rows FastAPI wrote. Supabase is our datastore + realtime transport — never a place where computation happens.*

> **Decision (this session):** the reporting website reads **exclusively from FastAPI** and we do **all** computation (humidity status, aggregation, histories, leaderboard, weather). See [docs/09](09-webapp-data-audit.md). This supersedes any earlier "dashboard reads Supabase directly" wording.

> RLS scopes the app's **Realtime subscription**: the authenticated role may `SELECT` (and thus receive change events for) public tree/sensor data and its own partnership rows, but may **not** write anything (all writes go through FastAPI's service role). Policy sketch in [docs/02](02-data-model.md) §RLS.

## 4. Data flows (the demo, step by step)

### 4.1 Sensor ingestion → realtime reward (demo steps 3–4)
1. ESP32 `POST /ingest/http` with `{ tree_id, raw_value, ... }` (raw ADC; `tree_id` is the device's string ref, matched via `sensors.device_ref`).
2. FastAPI **wraps** it into a LoRaWAN/Helium uplink envelope (base64 `frmpayload`, `rssi`, `snr`, `fcnt`) and forwards to its own `POST /ingest/lorawan`.
3. `/ingest/lorawan` **decodes** the payload, **calibrates** raw→moisture % using the sensor's dry/wet calibration, inserts a row into `sensor_readings`, and updates the tree's derived `health_state` / `moisture_pct` on `trees`.
4. If the tree **transitioned into the healthy band**, FastAPI runs the **immediate streak award** (demo path) on the active owner partnership.
5. Supabase **Realtime** pushes the updated `trees` row (and/or partnership) to the subscribed Flutter app → happy avatar + streak +1, with no polling.

### 4.2 Adoption (tree picking screen)
1. App `GET /trees/available?bbox=...` (FastAPI or Supabase) → un‑adopted trees in view.
2. App `POST /partnerships { tree_id }` → FastAPI checks tree is `available`, creates an `owner` partnership, flips tree to `adopted`. Returns the partnership.

### 4.3 Absence + coverage (demo steps 5 & 7)
1. App `POST /absences { tree_id, from_date, to_date }` → FastAPI records the absence, **freezes** the owner's streak for that tree, and lists the tree in the **caretaker pool**.
2. App (User 2) `GET /coverage/open?bbox=...` → trees needing a caretaker.
3. App `POST /coverage { absence_id }` → FastAPI creates a temporary `caretaker` partnership for `[from,to]`; caretaker now accrues streak for that tree.

### 4.4 Dashboard load (demo step 6)
1. Dashboard `GET /stats/overview` → totals, participation, health distribution, sensor status.
2. `GET /stats/by-stadtteil` → per‑district rows for the map/chart.
3. `GET /weather/forecast` + `GET /predictions` → forecast panel + "where to intervene" (mocked).

## 5. Deployment topology (demo day)

- **Supabase:** hosted project in the cloud (free tier). Holds DB + Auth + Realtime. The Flutter app connects to it for **Realtime only**; the website never does (it uses FastAPI).
- **FastAPI:** runs **locally on the demo laptop** (`uvicorn`), exposed via an **ngrok** HTTPS tunnel so:
  - the **real ESP32** can `POST` to a stable public URL regardless of the venue network, and
  - both frontends can call the same URL.
- **Config** via environment variables (`.env`, never committed):
  - `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY`
  - `SUPABASE_JWT_SECRET` (FastAPI verifies user JWTs with this)
  - `DATABASE_URL` (Postgres connection for SQLModel — use the Supabase **session pooler** URI)
  - `OPEN_METEO_BASE_URL` (default public), `KARLSRUHE_LAT`, `KARLSRUHE_LON`
  - `INGEST_SHARED_SECRET` (simple bearer the sensor/adapter sends)
- **Fallback for the realtime moment:** if venue WiFi blocks the ESP32, `scripts/fake_water.py --tree-id tree_001 --raw 1900` POSTs to `/ingest/http` so steps 3–4 still fire. (See [docs/06](06-seeding-and-mock-data.md) §9.)

## 6. Why this shape (rationale)

- **Supabase Realtime** removes the single biggest backend risk in a hackathon: building reliable websockets ourselves. The "wow" moment is free and robust.
- **FastAPI as a thin logic layer** keeps the *rules* (no‑competition, scoring, calibration, LoRaWAN) in clean, testable Python, and isolates the future ML cleanly.
- **All 130k trees in Postgres** make the city statistics genuinely real; **PostGIS bbox** keeps the map fast; **`stadtteil` partitioning** lets us concentrate the active fleet in the inner city with a trivial `WHERE`.

## 7. Cross‑cutting concerns

- **Idempotency:** ingestion is keyed by `(sensor_id, fcnt)`, falling back to `(sensor_id, measured_at)` (the real HTTP device has no `fcnt`), so a retried POST doesn't double‑count.
- **Auth:** FastAPI verifies the Supabase‑issued JWT (HS256, `SUPABASE_JWT_SECRET`) and derives the user id; the service‑role key is used for privileged writes only.
- **Time:** store all timestamps in UTC (`timestamptz`); the daily cron uses Europe/Berlin local day boundaries.
- **Observability:** structured request logs on FastAPI; a `/healthz` endpoint.
- **Secrets:** service‑role key + JWT secret live only in the FastAPI env, never shipped to a frontend.
