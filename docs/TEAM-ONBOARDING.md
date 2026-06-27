# Baumpate / HackXPlore — Team Onboarding Guide

> **Private handoff doc.** Send this file to teammates together with secrets (`.env` values) over a **secure channel** — never commit real keys to git.

---

## 1. What this project is

**Baumpate** — smart watering for urban trees (VEGA / HackXPlore Karlsruhe).

- Citizens adopt trees, keep soil healthy (gamified streaks).
- ESP32 + capacitive sensor reports **raw ADC** moisture.
- City gets a **React transparency dashboard** + (mocked) shortage prediction.
- **Backend:** Python FastAPI + Supabase Postgres (PostGIS, Auth, Realtime).
- **Frontends (parallel teams):**
  - **React dashboard** — in this repo under `hackxplore2026-webapp/`
  - **Flutter citizen app** — separate repo; talks to same FastAPI + Supabase Realtime

**Read first (in repo):**

| Doc                                                               | Purpose                             |
| ----------------------------------------------------------------- | ----------------------------------- |
| [`SPEC.md`](../SPEC.md)                                           | Product index + 3‑minute demo spine |
| [`docs/01-architecture.md`](01-architecture.md)                   | Who talks to what                   |
| [`docs/03-api-contract.md`](03-api-contract.md)                   | HTTP API (source of truth)          |
| [`docs/08-frontend-data-mapping.md`](08-frontend-data-mapping.md) | Flutter enum mapping                |
| [`docs/09-webapp-data-audit.md`](09-webapp-data-audit.md)         | React ↔ FastAPI wiring              |

---

## 2. Architecture (who connects to what)

```
ESP32 sensor ──POST /ingest/http──► FastAPI ──writes──► Supabase Postgres
                                         │
React dashboard ──REST only──────────────┤
                                         │
Flutter app ──REST (reads/writes/logic)──┤
         └── Realtime subscribe only ───► Supabase (push when FastAPI writes)
```

**Rules:**

- **React website → FastAPI only** (no direct Supabase for data).
- **Flutter → FastAPI** for all logic; **Supabase Realtime** only as a push channel.
- **ESP32 → FastAPI** only (never Supabase).
- **All business logic** lives in FastAPI, not in frontends or Supabase functions.

---

## 3. Repository layout

```
HackXPlore/                          ← monorepo root (git root)
├── app/                             ← FastAPI backend
│   ├── main.py                      ← entry, mounts /api/v1
│   ├── routers/                     ← HTTP endpoints
│   ├── services/                    ← ingestion, scoring, weather
│   ├── calibration.py, lorawan.py   ← sensor pipeline
│   └── seed/                        ← demo + mock data
├── supabase/migrations/             ← SQL schema (PostGIS, RLS)
├── tests/                           ← pytest
├── scripts/                         ← fake_water, make_thirsty, …
├── docs/                            ← specs + this file
├── data/raw/                        ← Karlsruhe tree GeoJSON
├── hackxplore2026-webapp/           ← React city dashboard
│   └── src/lib/api/                 ← FastAPI client + mappers
├── .env.example                     ← backend env template
├── Makefile
└── pyproject.toml                   ← uv / Python 3.12
```

---

## 4. Prerequisites

Install on your machine:

| Tool        | Version | Install                                            |
| ----------- | ------- | -------------------------------------------------- |
| **Python**  | 3.12+   | [python.org](https://www.python.org/) or Homebrew  |
| **uv**      | latest  | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **Node.js** | 18+     | [nodejs.org](https://nodejs.org/) or `nvm`         |
| **git**     | any     | —                                                  |

Optional: **ngrok** for exposing local API to ESP32 or remote teammates.

You do **not** need Docker unless running Supabase locally (`supabase start`).

---

## 5. Get the code

```bash
git clone git@github.com:FlorianSchwieren/hackxplore2026-webapp.git
cd hackxplore2026-webapp   # repo name may change; root contains app/ + hackxplore2026-webapp/
```

---

## 6. Secrets & environment files

`.env` files are **gitignored**. Your team lead shares values via **1Password / Signal / Supabase invite** — not in GitHub.

### 6.1 Backend — copy root `.env`

```bash
cp .env.example .env
```

Fill in `.env` (get values from team lead or Supabase Dashboard → **Project Settings**):

```env
# FastAPI
API_PREFIX=/api/v1
ENVIRONMENT=development
DEV_AUTH_DISABLED=true          # local dev: skip JWT — acts as Taylor Team (see §7.1)

# Supabase / Postgres
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_PUBLISHABLE_KEY=<from Dashboard → API>
SUPABASE_SECRET_KEY=<from Dashboard → API>    # service role — backend ONLY
SUPABASE_JWKS_URL=https://<project-ref>.supabase.co/auth/v1/.well-known/jwks.json
SUPABASE_JWT_SECRET=<optional if using JWKS>

# Database — Session pooler URI (Dashboard → Database → Connection string)
# URL-encode special chars in password: ! → %21, ? → %3F, etc.
DATABASE_URL=postgresql://postgres.<project-ref>:<password>@<pooler-host>:5432/postgres

# Sensor ingest (shared with ESP32 + demo scripts)
INGEST_SHARED_SECRET=<agree on a team secret>

# Weather / Karlsruhe (defaults usually fine)
OPEN_METEO_BASE_URL=https://api.open-meteo.com/v1
KARLSRUHE_LAT=49.0069
KARLSRUHE_LON=8.4037

# Scoring tunables (defaults usually fine)
OUTLIER_RAW_MARGIN=250
SMOOTHING_WINDOW=5
STATE_DEBOUNCE_READINGS=2
INGEST_DEDUPE_WINDOW_SECONDS=5
THRIVING_STREAK_THRESHOLD=7
RAIN_PENALTY_SKIP_PRECIP_MM_24H=5.0
UNCOVERED_ABSENCE_PROTECTS_STREAK=true
```

**Aliases:** `app/config.py` also accepts `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_ROLE_KEY` instead of publishable/secret names.

### 6.2 Frontend — copy webapp `.env`

```bash
cd hackxplore2026-webapp
cp .env.example .env
```

For **live backend** (recommended):

```env
VITE_USE_MOCK_DATA=false
VITE_API_BASE_URL=http://localhost:8000/api/v1

# Optional — only if you add Supabase client usage later
VITE_SUPABASE_URL=https://<project-ref>.supabase.co
VITE_SUPABASE_ANON_KEY=<publishable/anon key>

# Optional map tiles (empty = OpenFreeMap fallback on localhost)
VITE_STADIA_API_KEY=
```

For **UI-only without backend**:

```env
VITE_USE_MOCK_DATA=true
```

---

## 7. First-time setup (full stack)

Run from **repo root**:

```bash
# 1. Backend dependencies
uv sync --extra dev

# 2. Database schema (once, or after migration changes)
make migrate

# 3. Seed data (~4k inner-city trees, 1k sensors, 300 users, demo Berta)
make seed

# 4. (Optional) Reset demo spine before a pitch
uv run python -m app.seed demo

# 5. Start API
make run
# → http://localhost:8000
```

In a **second terminal**:

```bash
cd hackxplore2026-webapp
npm install
npm run dev
# → http://localhost:5173
```

### Verify

| Check              | URL / command                               |
| ------------------ | ------------------------------------------- |
| API alive          | http://localhost:8000/healthz               |
| API docs (Swagger) | http://localhost:8000/api/v1/docs           |
| Stats              | http://localhost:8000/api/v1/stats/overview |
| Dashboard map      | http://localhost:5173                       |
| Dashboard stats    | http://localhost:5173/stats                 |
| Tests              | `make test`                                 |

Expected stats (after seed): ~**4,377 trees**, ~**1,001 sensors**, ~**312 users**.

### 7.1 Team demo profile (no JWT needed)

With `DEV_AUTH_DISABLED=true`, every **user** route runs as **Taylor Team** — a seeded profile with **5 trees** and **10 co-partners**. No `Authorization` header required.

Seed (included in `make seed`, or alone):

```bash
uv run python -m app.seed team_demo
```

| Field | Value |
| ----- | ----- |
| Display name | Taylor Team |
| Email | `team@baumpate.demo` |
| User ID | `7e33b42d-e8ff-5261-91fe-c2f0d8fc44c0` |
| Trees | `TeamDemo-1` … `TeamDemo-5` (owner on each) |
| Co-partners | 10 (`Casey 1`, `Jordan 2`, … — 2 members per tree) |

Try without auth:

```bash
curl http://localhost:8000/api/v1/me
curl http://localhost:8000/api/v1/me/trees
curl http://localhost:8000/api/v1/me/co-partners
```

Optional override: `DEV_AUTH_USER_ID=<uuid>` in `.env`.

---

## 8. Daily dev commands

### Backend (repo root)

```bash
make run          # uvicorn with reload on :8000
make test         # pytest
make lint         # ruff
make seed         # re-run all seeds (idempotent)
make migrate      # apply SQL migrations
```

### Frontend

```bash
cd hackxplore2026-webapp
npm run dev       # Vite dev server :5173
npm run typecheck
npm run build     # production build
```

### Demo control scripts

```bash
# Reset Berta (demo tree) to thirsty
uv run python scripts/make_thirsty.py

# Simulate watering (healthy transition + streak)
uv run python scripts/fake_water.py --raw 1900

# Optional: jitter mock sensor readings
uv run python scripts/mock_stream.py
```

### Manual ingest (curl)

```bash
curl -X POST http://localhost:8000/api/v1/ingest/http \
  -H "Authorization: Bearer <INGEST_SHARED_SECRET>" \
  -H "Content-Type: application/json" \
  -d '{"tree_id":"tree_001","raw_value":1900,"fcnt":99999}'
```

---

## 9. Important URLs (local)

| Surface         | URL                                       |
| --------------- | ----------------------------------------- |
| React map       | http://localhost:5173/                    |
| React stats     | http://localhost:5173/stats               |
| FastAPI Swagger | http://localhost:8000/api/v1/docs         |
| FastAPI ReDoc   | http://localhost:8000/api/v1/redoc        |
| OpenAPI JSON    | http://localhost:8000/api/v1/openapi.json |
| Health          | http://localhost:8000/healthz             |

**Karlsruhe map bbox** (used by frontend): `8.35,48.98,8.45,49.03`

---

## 10. API overview (FastAPI `/api/v1`)

Full contract: [`docs/03-api-contract.md`](03-api-contract.md).

| Area       | Key endpoints                                                      |
| ---------- | ------------------------------------------------------------------ |
| Health     | `GET /healthz`                                                     |
| Ingest     | `POST /ingest/http`, `POST /ingest/lorawan` (Bearer ingest secret) |
| Map        | `GET /trees?bbox=…`, `GET /trees/{id}`, `GET /trees/{id}/readings` |
| Adopt      | `POST /partnerships`, `GET /me/trees`, `GET /me/co-partners`       |
| Absence    | `POST /absences`, `GET /coverage/open`, `POST /coverage`           |
| User       | `GET /me`, `PATCH /me`, `GET /me/co-partners`                      |
| Dashboard  | `GET /stats/overview`, `GET /stats/by-stadtteil`, `GET /sensors`   |
| Weather    | `GET /weather/forecast`                                            |
| Prediction | `GET /predictions` (mocked)                                        |

**Auth:**

- User routes: `Authorization: Bearer <supabase_jwt>`
- Local dev: set `DEV_AUTH_DISABLED=true` in root `.env` to skip JWT
- Ingest: `Authorization: Bearer <INGEST_SHARED_SECRET>`

---

## 11. React dashboard — how it talks to the backend

Live mode (`VITE_USE_MOCK_DATA=false`):

| Hook                | FastAPI endpoint               |
| ------------------- | ------------------------------ |
| `useTrees`          | `GET /trees?bbox=…&limit=2000` |
| `useTreeDetail`     | `GET /trees/{id}`              |
| `useSensors`        | `GET /sensors`                 |
| `useTreeReadings`   | `GET /trees/{id}/readings`     |
| `useNetworkStats`   | `GET /stats/overview`          |
| `useStadtteilStats` | `GET /stats/by-stadtteil`      |
| `useWeatherQuery`   | `GET /weather/forecast`        |

Implementation: `hackxplore2026-webapp/src/lib/api/client.ts` + `mappers.ts`.

Mock mode: hooks return data from `src/lib/mock/*` — no backend required.

---

## 12. Flutter app team

You need:

1. **FastAPI base URL** — same as `VITE_API_BASE_URL` (local or ngrok)
2. **Supabase URL + anon/publishable key** — for Auth login + Realtime subscribe only
3. **Do not** embed the service role key in the app
4. Contract mapping: [`docs/08-frontend-data-mapping.md`](08-frontend-data-mapping.md)

Realtime tables: `trees`, `tree_partnerships`, `sensor_readings` (after FastAPI writes).

Demo users (seeded): `alex@baumpate.demo`, `sam@baumpate.demo` — create matching Supabase Auth users or use credentials from team lead.

---

## 13. ESP32 / hardware team

Device POSTs to FastAPI **only**:

```
POST https://<your-api-host>/api/v1/ingest/http
Authorization: Bearer <INGEST_SHARED_SECRET>
Content-Type: application/json

{
  "tree_id": "tree_001",
  "raw_value": 2480,
  "battery_voltage": null,
  "rssi": -47,
  "created_at": "2026-06-27T14:03:00Z"
}
```

- `tree_id` matches `sensors.device_ref` in DB (demo: `tree_001` → tree **Berta**).
- Backend **ignores** any device-computed moisture; it recalibrates from `raw_value`.
- For demo day: expose local API via **ngrok** → `ngrok http 8000` → give hardware team the HTTPS URL.

---

## 14. Demo spine (3-minute pitch)

1. User 1 gets push: tree thirsty (Flutter — may be mocked).
2. Opens app → sad avatar (Berta, low moisture).
3. **Physical watering** → ESP32 POSTs raw reading.
4. Backend → healthy band → streak +1 → Flutter Realtime updates avatar.
5. User 1 declares **absence**.
6. **React dashboard** → city stats, health distribution, sensors.
7. User 2 covers absence → earns score by helping.

**Reset before demo:**

```bash
uv run python -m app.seed demo
uv run python scripts/make_thirsty.py   # if you need thirsty start again
```

**Demo entities:**

| Entity          | Value                                |
| --------------- | ------------------------------------ |
| Demo tree       | **Berta** (adopted, Innenstadt-West) |
| Real sensor ref | `tree_001`                           |
| Demo users      | Alex + Sam (`*@baumpate.demo`)       |

---

## 15. Database (shared Supabase project)

Everyone on the team can use the **same** Supabase project (recommended for hackathon).

| Action       | Who           | Command                   |
| ------------ | ------------- | ------------------------- |
| Apply schema | Once per env  | `make migrate`            |
| Load data    | After migrate | `make seed`               |
| Reset demo   | Before pitch  | `python -m app.seed demo` |

**Current seeded scale** (inner city only):

| Table        | ~Count                    |
| ------------ | ------------------------- |
| trees        | 4,377                     |
| sensors      | 1,001 (1 real `tree_001`) |
| profiles     | 302                       |
| partnerships | ~588 active               |
| absences     | 8 open                    |

**Full city ~130k trees** (optional, slow):

```bash
uv run python -m app.seed trees --citywide
```

Supabase Dashboard: https://supabase.com/dashboard → your project → **Table Editor** / **SQL Editor**.

---

## 16. Remote / demo-day setup (ngrok)

When teammates or ESP32 are **not on your LAN**:

```bash
# Terminal 1
make run

# Terminal 2
ngrok http 8000
```

Share the ngrok HTTPS URL:

- Hardware: `POST https://xxxx.ngrok-free.app/api/v1/ingest/http`
- Frontend: `VITE_API_BASE_URL=https://xxxx.ngrok-free.app/api/v1`
- Flutter: same base URL

Keep `INGEST_SHARED_SECRET` in sync across device + backend `.env`.

---

## 17. Troubleshooting

| Problem                           | Fix                                                                |
| --------------------------------- | ------------------------------------------------------------------ |
| Map empty, stats zero             | Backend not running; or `VITE_USE_MOCK_DATA=false` without API     |
| API 503 “Database not configured” | Set `DATABASE_URL` in root `.env`                                  |
| DB connection fails               | Check pooler URI; URL-encode password special chars                |
| `make migrate` fails              | Ensure PostGIS enabled (Supabase has it); check `DATABASE_URL`     |
| Ingest 401                        | Wrong `INGEST_SHARED_SECRET` in Authorization header               |
| Ingest 409 duplicate              | Add unique `"fcnt"` or wait 5s between identical readings          |
| Ingest 404 tree_001               | Run `python -m app.seed demo`                                      |
| Git push blocked (secrets)        | Never commit keys; use `.env` only; rotate leaked keys in Supabase |
| Port in use                       | `lsof -ti :8000 \| xargs kill -9` (same for `:5173`)               |

---

## 18. What the team lead sends privately

Checklist for the person setting up shared access:

- [ ] Git repo URL + branch (`main`)
- [ ] Supabase **project invite** (preferred) **or** filled `.env` via secure share
- [ ] `DATABASE_URL` (session pooler + password)
- [ ] `SUPABASE_URL`, publishable key, **service role secret** (backend devs only)
- [ ] `INGEST_SHARED_SECRET` (backend + hardware)
- [ ] `DEV_AUTH_DISABLED=true` note for local dev
- [ ] Demo user passwords (if Supabase Auth users created)
- [ ] ngrok URL on demo day (if applicable)
- [ ] This file: `docs/TEAM-ONBOARDING.md`

**Never commit:** `.env`, `hackxplore2026-webapp/.env`, database passwords, service role keys.

---

## 19. Role-specific quick start

### Backend developer

```bash
cp .env.example .env   # fill secrets
uv sync --extra dev && make migrate && make seed && make run
make test
open http://localhost:8000/api/v1/docs
```

### React dashboard developer

```bash
# assume backend running elsewhere or locally
cd hackxplore2026-webapp
cp .env.example .env   # VITE_USE_MOCK_DATA=false, VITE_API_BASE_URL=...
npm install && npm run dev
open http://localhost:5173
```

### Flutter developer

- Get FastAPI URL + Supabase anon key from team lead
- Read `docs/03-api-contract.md` + `docs/08-frontend-data-mapping.md`
- Subscribe Realtime to `trees` / `tree_partnerships` after FastAPI writes

### Hardware developer

- Get ngrok or public API URL + `INGEST_SHARED_SECRET`
- POST raw ADC to `/ingest/http` with `tree_id: "tree_001"`
- Test with `scripts/fake_water.py` first

---

## 20. Product rules (do not break)

1. **Cooperative, never competitive** — only `available` trees can be adopted; `POST /partnerships` → 409 on taken trees.
2. **Sensor sends raw ADC** — backend calibrates; ignore device moisture fields.
3. **Score = Σ per-tree streaks** (not a flat counter).
4. **Append-only history** — never delete/update `sensor_readings`, `weather_snapshots`, `absences`.
5. **React → FastAPI only** for data.
6. **Demo spine wins** — if stuck for time, prioritize ingest + Realtime + dashboard stats.

---

_Last updated: 2026-06-27 — matches monorepo layout with backend at root + `hackxplore2026-webapp/`._
