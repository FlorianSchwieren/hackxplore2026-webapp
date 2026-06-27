# 07 — Implementation Plan

> A phased, step‑by‑step build plan for the agents/devs who implement the backend. Each milestone has **tasks**, **files**, and **acceptance criteria**. Build in order; each milestone leaves the system demoable a bit further along. The demo spine ([SPEC §4](../SPEC.md)) is the priority — if time runs short, the spine is **M0–M6 + realtime + M9** (dashboard stats are needed for demo step 6); **M7 weather** and **M8 prediction** are enhancements.

## 0. Proposed repo layout (backend)

```
HackXPlore/
├── SPEC.md  CLAUDE.md  AGENTS.md(->CLAUDE.md)
├── docs/00..09
├── data/raw/karlsruhe_trees_citycenter.geojson
├── supabase/
│   ├── migrations/0001_init.sql        # postgis, tables, indexes, realtime publication
│   └── migrations/0002_rls.sql         # row-level security policies
├── app/
│   ├── main.py                         # FastAPI app + routers
│   ├── config.py                       # env + tunables (docs/05 §5)
│   ├── db.py                           # SQLModel engine/session (DATABASE_URL)
│   ├── auth.py                         # verify Supabase JWT → current user id
│   ├── models.py                       # SQLModel tables (mirror docs/02)
│   ├── schemas.py                      # Pydantic request/response (mirror docs/03)
│   ├── calibration.py                  # raw_to_pct, health_score, health_state
│   ├── mapping.py                      # to_app_species / to_app_health_state (docs/08)
│   ├── lorawan.py                      # encode_uplink / decode_uplink (docs/04)
│   ├── routers/{ingest,trees,partnerships,absences,stats,weather,predictions,me}.py
│   ├── services/{scoring,ingestion,coverage,weather}.py
│   ├── cron.py                         # daily evaluation entrypoint
│   └── seed/{species,trees,sensors,readings,users,partnerships,demo}.py
├── scripts/{fake_water.py,make_thirsty.py,mock_stream.py}
├── tests/
├── pyproject.toml  (uv)   .env.example   Makefile   README.md
```

## Supabase setup — who does what (the only manual step)

**You (once, in the Supabase dashboard, ~5 min):**
1. Create a project (org + name + region **EU / Frankfurt** for Karlsruhe + a DB password).
2. Copy these into our `.env` (Project Settings → API / Database):
   - `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`
   - `DATABASE_URL` — the **session pooler** connection string (+ your DB password)

Example shape (use values from **your** Supabase dashboard — never commit real keys):

```env
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_PUBLISHABLE_KEY=<from Project Settings → API>
SUPABASE_SECRET_KEY=<from Project Settings → API>
SUPABASE_JWKS_URL=https://<project-ref>.supabase.co/auth/v1/.well-known/jwks.json
```

That's all. You do **not** create tables, enable extensions, write RLS policies, or add users by hand.

**Automated (agents, via the service key + `DATABASE_URL`):**
- `create extension postgis`, all tables/indexes, RLS policies, and the Realtime publication — through SQL migrations (`make migrate`).
- Seed species/trees/sensors/readings/users/partnerships + the demo scenario (`make seed`).
- Create the 2 demo auth users via the Supabase Admin API (service key).
- Run FastAPI + ngrok.

**Alternative (no cloud account):** `supabase start` runs the whole stack locally in Docker (Postgres + Auth + Realtime + Studio). Good for dev; for the live demo a cloud project is more reliable for the frontends to reach. The steps above are otherwise identical.

> Agents can scaffold **M0–M1** (app skeleton, migrations, seed scripts) **before** credentials exist; credentials are only needed to *run* migrations/seed against the live DB.

## M0 — Project & infra setup
**Tasks:** init uv project (`pyproject.toml`, Python 3.12); add FastAPI, uvicorn, SQLModel, psycopg[binary], httpx, supabase, pyjwt, python‑dotenv. **Supabase project must exist** (the one manual step — see §"Supabase setup" above) so we have the URL/keys/JWT‑secret/`DATABASE_URL`. Wire `.env.example` (all vars from [docs/01](01-architecture.md) §5). `app/main.py` with `/healthz`; `app/auth.py` (verify Supabase JWT → current user id). Makefile (`run`, `seed`, `test`, `migrate`).
**Files:** `pyproject.toml`, `app/main.py`, `app/config.py`, `app/db.py`, `app/auth.py`, `.env.example`, `Makefile`.
**Done when:** `make run` serves `GET /healthz → {status:ok}`; DB reachable; a valid Supabase JWT resolves to a user id.

## M1 — Schema, migrations & tree seed
**Tasks:** write `0001_init.sql` — `create extension postgis`; all tables + indexes from [docs/02](02-data-model.md); `alter publication supabase_realtime add table trees, tree_partnerships;` (for the app's Realtime). SQLModel models mirroring the tables. `seed/species.py` ([docs/06](06-seeding-and-mock-data.md) §3) and `seed/trees.py` (paginated citywide load + species resolution).
**Files:** `supabase/migrations/0001_init.sql`, `app/models.py`, `app/seed/species.py`, `app/seed/trees.py`.
**Done when:** all ~130k trees in `trees`, each with a `species_profile_id`; `GET /trees?bbox=<inner city>` returns rows (after M3 route, or a quick temp query).

## M2 — Ingestion + LoRaWAN adapter
**Tasks:** `calibration.py` (`raw_to_pct`, `health_score`, `health_state`); `lorawan.py` (`encode_uplink`, `decode_uplink`); `routers/ingest.py` for `POST /ingest/http` (real `{tree_id, raw_value, …}` shape) → wrap → `POST /ingest/lorawan` → decode → look up sensor by `device_ref` → store reading (with denormalized `tree_id`) → **plausibility gate + median smoothing + debounce** ([docs/04](04-sensor-and-lorawan.md) §3) → update `trees`/`sensors` caches. Idempotency `(sensor_id, fcnt)` → fallback `(sensor_id, measured_at)`. ([docs/04](04-sensor-and-lorawan.md))
**Files:** `app/calibration.py`, `app/lorawan.py`, `app/routers/ingest.py`, `app/services/ingestion.py`.
**Done when:** posting a raw reading for a seeded sensor inserts a `sensor_readings` row and updates the tree's `moisture_pct/health_*`; replays don't duplicate; an outlier raw value is stored but does **not** move tree health.

## M3 — Trees, partnerships, map reads
**Tasks:** `routers/trees.py` (`GET /trees` bbox+filters via PostGIS, `/trees/{id}`, `/trees/available`, `GET /trees/{id}/readings`, `PATCH /trees/{id}/name`) returning app‑shaped fields (`title`, `species_app`, `health_state_app`, `coordinates`, `owner_ids` via `mapping.py`); `routers/partnerships.py` (`POST /partnerships` adopt with `available` guard, `GET /me/trees`, invite, leave); `routers/me.py` (`GET/PATCH /me`, `/notifications`). User endpoints use the `auth.py` JWT dependency. Enforce **no‑competition** (409 on adopting an adopted tree).
**Files:** `app/routers/trees.py`, `app/routers/partnerships.py`, `app/routers/me.py`, `app/mapping.py`, `app/schemas.py`.
**Done when:** can adopt an available tree (tree → adopted), cannot adopt an adopted one; `GET /me/trees` returns score + trees; `GET /trees/{id}/readings` returns the series; bbox queries are fast (GIST index).

## M4 — Scoring (streak/score) + cron + demo award
**Tasks:** `services/scoring.py` implementing the streak rules + `score = Σ streak` ([docs/05](05-scoring-and-gamification.md)); `cron.py` daily evaluation (run via Supabase scheduled function or a local scheduler for the demo); hook the **immediate‑award** into ingestion (transition into healthy band). `last_eval_date` double‑count guard.
**Files:** `app/services/scoring.py`, `app/cron.py`; edit `app/services/ingestion.py`.
**Done when:** watering the demo tree (M2 ingest) yields owner `streak +1` and updated `score`; running the cron twice in a day doesn't double count; the 1000→909 example reproduces in a unit test.

## M5 — Absences & coverage (the handoff)
**Tasks:** `routers/absences.py` (`POST /absences` → freeze streak + open pool; `GET /coverage/open`; `POST /coverage` → caretaker partnership). Expiry handling (caretaker ends, freeze clears).
**Files:** `app/routers/absences.py`, `app/services/coverage.py`.
**Done when:** User 1 declares absence (streak frozen, tree in pool); User 2 covers (caretaker partnership, accrues streak); owner streak preserved.

## M6 — Dashboard stats
**Tasks:** `routers/stats.py` (`/stats/overview`, `/stats/by-stadtteil`, `/sensors`) with SQL aggregates; `city_health_score`.
**Files:** `app/routers/stats.py`.
**Done when:** `/stats/overview` returns the totals/health‑distribution/sensor‑status shape from [docs/03](03-api-contract.md) §8 against seeded data.

## M7 — Weather + realtime/RLS hardening
**Tasks:** `routers/weather.py` + `services/weather.py` (Open‑Meteo proxy + `weather_snapshots` write); scheduled weather fetch. `0002_rls.sql` policies ([docs/02](02-data-model.md) §RLS); verify the app's anon/auth role can read but not write partnership rows; confirm Realtime pushes `trees`/`tree_partnerships` changes. Implement the **heavy‑rain streak carve‑out** ([docs/05](05-scoring-and-gamification.md) §4.1).
**Files:** `app/routers/weather.py`, `app/services/weather.py`, `supabase/migrations/0002_rls.sql`.
**Done when:** `GET /weather/forecast` returns Karlsruhe forecast + writes a snapshot; a FastAPI write to `trees` is received by a Supabase Realtime subscriber.

## M8 — Prediction stub
**Tasks:** `routers/predictions.py` returning the mocked contract ([docs/03](03-api-contract.md) §9) computed from current readings + a simple heuristic (dry + forecast + absence) so it looks plausible. Clearly labelled `model:"mock-v0"`.
**Files:** `app/routers/predictions.py`.
**Done when:** `GET /predictions` returns ranked at‑risk trees + per‑district humidity trend.

## M9 — Demo hardening
**Tasks:** `seed/demo.py` (authoritative scenario, [docs/06](06-seeding-and-mock-data.md) §8); `scripts/fake_water.py`, `make_thirsty.py`; ngrok runbook; end‑to‑end rehearsal of the 7‑step spine; smoke tests.
**Done when:** the full demo runs start‑to‑finish twice in a row using only `seed/demo.py` + the scripts.

---

## Parallelization (if multiple agents)
- **Agent A:** M1→M2→M4 (data + ingestion + scoring — the spine).
- **Agent B:** M3→M5 (partnerships + coverage).
- **Agent C:** M6→M8 (dashboard + weather + prediction).
- Integrate at M9. Contracts in [docs/03](03-api-contract.md) let frontends and B/C proceed against stubs early.

## Testing priorities (limited time → test the spine)
1. `raw_to_pct` + `health_state` boundaries (unit).
2. Streak math incl. the 1000→909 example and the freeze/cron double‑count guard (unit).
3. Ingestion idempotency (`fcnt` / `measured_at` fallback) + outlier rejection (unit/integration).
4. Adopt no‑competition `409` (integration).
5. End‑to‑end: ingest → tree health change → streak award (integration).

## Demo‑day checklist
- [ ] Supabase up; `make seed all`; then `python -m app.seed demo` last.
- [ ] FastAPI running; ngrok tunnel up; note the HTTPS URL; share with frontend + flash to ESP32.
- [ ] Real sensor calibrated (`calibration_dry/wet` set); test one real `POST /ingest/http`.
- [ ] Verify Realtime: water once → app updates → then `make_thirsty.py --tree-id tree_001` to reset.
- [ ] Dashboard `/stats/overview` looks city‑wide.
- [ ] `fake_water.py` ready as the safety net.
- [ ] Re‑run `seed/demo.py` immediately before walking on stage.

---

## Later (post‑hackathon, already enabled by the schema)
- **Real prediction model:** train on `sensor_readings` (time series) + `weather_snapshots` + `absences` history → replace the `/predictions` stub. The append‑only history tables exist for exactly this.
- **Real push notifications** (FCM/APNs/Web Push) replacing the app‑side mock.
- **Real Helium gateway:** point it at `/ingest/lorawan` — no backend change (same envelope/decoder).
- **Named teams** (`teams`/`team_members`) if the product wants managed groups.
