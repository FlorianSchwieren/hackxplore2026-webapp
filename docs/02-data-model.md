# 02 — Data Model

> Postgres (Supabase) schema. Types are Postgres types. `id` columns are `uuid default gen_random_uuid()` unless noted. All timestamps are `timestamptz` (UTC). PostGIS is enabled (`create extension postgis`).

## 1. Entity overview

```
auth.users (Supabase)         species_water_profiles
      │ 1:1                            │ lookup by category/species
      ▼                                ▼
   profiles ──< tree_partnerships >── trees ──1:1── sensors ──< sensor_readings
      │                │                 │
      │                │ owner/member/   │
      │                │ caretaker       │
      └──< absences >──┘                 └──(geom, stadtteil, status)

weather_snapshots   (history)        notifications (optional/feed)
```

Key relationships:
- A **tree** has **many partnerships** (M:N users↔trees via `tree_partnerships`).
- A **tree** has **0..1 sensor**; a **sensor** has **many readings** (append‑only time series).
- An **absence** belongs to a (user, tree) and may be **covered** by a `caretaker` partnership.
- **Score is derived** = sum of a user's partnership streaks (cached on `profiles.score`).

---

## 2. Tables

### 2.1 `profiles` — app user (extends Supabase `auth.users`)
| Column | Type | Notes |
|---|---|---|
| `id` | uuid PK | = `auth.users.id` (FK) |
| `display_name` | text | shown in app (app `User.name`) |
| `email` | text | mirror of auth email |
| `avatar_url` | text null | app `User.avatarUrl` |
| `score` | int not null default 0 | **cached** = Σ partnership streaks; recomputed by cron + on events |
| `notify_help_opt_in` | bool default false | "notify me about thirsty trees nearby" toggle |
| `created_at` | timestamptz default now() | |

> Seeded with 2 real demo users + ~300 fake users (see [docs/06](06-seeding-and-mock-data.md)).
> Derived for the app: `totalTreesCount` = count of active partnerships. (No liters — a soil sensor can't measure water volume; see §2.10 and [docs/08](08-frontend-data-mapping.md) §5.)

### 2.2 `trees` — every Karlsruhe tree (from the geoportal)
| Column | Type | Notes |
|---|---|---|
| `id` | uuid PK | internal |
| `external_id` | bigint unique not null | source `objectid` (stable; `lfdbnr` is often null → not the PK) |
| `lfdbnr` | int null | source running number (often null) |
| `artdeut` | text null | German species (~72% filled citywide) |
| `artlat` | text null | Latin species |
| `baumart_allgemein` | text not null | coarse category — always present (`Laubbaum/Nadelbaum/Obstbaum/Palme/Topograph. Baum/unbekannt`) |
| `baumgruppe` | text null | e.g. `Einzelbaum` |
| `stadtteil` | text not null | district — **partition key** for "inner city" subset |
| `geom` | geometry(Point,4326) not null | lon/lat; **GIST index** for bbox queries |
| `name` | text null | citizen‑given name; UI default e.g. "Baum #<external_id>" |
| `status` | text not null default 'available' | `available` \| `adopted` |
| `species_profile_id` | uuid null FK→species_water_profiles | resolved at seed time |
| **derived/cache** | | updated on each reading |
| `moisture_pct` | numeric(5,2) null | latest calibrated moisture |
| `health_score` | int null | 0–100 normalized vs species profile |
| `health_state` | text null | `thriving/healthy/thirsty/critical/overwatered` |
| `last_reading_at` | timestamptz null | |
| `created_at` | timestamptz default now() | |

Indexes: `gist(geom)`, `btree(stadtteil)`, `btree(status)`, `btree(health_state)`.

> **Sensored vs not:** a tree is "monitored" iff a `sensors` row points at it. Un‑sensored trees still appear on the map but have null health.

### 2.3 `species_water_profiles` — authored lookup (the missing moisture optima)
The dataset has species but **no moisture preference** — we author it.
| Column | Type | Notes |
|---|---|---|
| `id` | uuid PK | |
| `match_kind` | text not null | `category` \| `species_lat` |
| `match_value` | text not null unique | e.g. `Laubbaum` or `Tilia cordata` |
| `optimal_min_pct` | numeric not null | lower edge of healthy band |
| `optimal_max_pct` | numeric not null | upper edge of healthy band |
| `dry_critical_pct` | numeric not null | below → `critical` |
| `wet_critical_pct` | numeric not null | above → `overwatered` |
| `drought_tolerance` | text | `low/medium/high` (narrative) |
| `priority` | int default 0 | higher = more specific (species beats category) |
| `notes` | text null | |

Resolution at seed time: pick the highest‑priority profile matching the tree's `artlat` (`species_lat`), else its `baumart_allgemein` (`category`), else a `default` profile. Concrete values in [docs/06](06-seeding-and-mock-data.md) §species.

### 2.4 `sensors` — one per monitored tree (1:1)
| Column | Type | Notes |
|---|---|---|
| `id` | uuid PK | |
| `device_eui` | text unique not null | LoRaWAN‑style id (synthesised as `BAUMPATE-<device_ref>` for the adapter) |
| `device_ref` | text unique not null | the string the device actually sends as `tree_id` (e.g. `tree_001`, `MOCK-0001`) — **lookup key for ingestion** |
| `tree_id` | uuid unique not null FK→trees | 1:1 |
| `status` | text not null default 'working' | `working` \| `inactive` \| `defect` (for the maintenance view) |
| `is_real` | bool not null default false | exactly one true row = the physical demo sensor |
| `calibration_dry` | int not null | raw ADC at 0% — **measure in dry soil** for the real probe (example nominal 3099) |
| `calibration_wet` | int not null | raw ADC at 100% — **measure in saturated soil**, not water (example nominal 1500; see [docs/04](04-sensor-and-lorawan.md) §2.1) |
| `installed_at` | timestamptz default now() | |
| `last_seen_at` | timestamptz null | updated on each reading; drives `inactive` detection |
| `created_at` | timestamptz default now() | |

> Capacitive sensors read **lower raw values when wetter** (`dry > wet`); calibration maps `raw → pct` ([docs/04](04-sensor-and-lorawan.md) §2). Calibration is **per‑probe and must be measured** (sample values were random test data). The real device reports `tree_id="tree_001"` → matched via `device_ref`.

### 2.5 `sensor_readings` — append‑only time series (ML foundation)
| Column | Type | Notes |
|---|---|---|
| `id` | bigserial PK | |
| `sensor_id` | uuid not null FK→sensors | |
| `tree_id` | uuid not null FK→trees | denormalized (sensor is 1:1 with its tree) — lets the detail chart / dashboard query readings by tree directly |
| `raw` | int not null | raw ADC as received (source of truth) |
| `moisture_pct` | numeric(5,2) not null | **our** calibrated value |
| `is_outlier` | bool not null default false | failed the plausibility gate ([docs/04](04-sensor-and-lorawan.md) §3); stored but does **not** move tree health |
| `measured_at` | timestamptz not null | device `created_at` if provided, else server time |
| `received_at` | timestamptz default now() | |
| `fcnt` | int null | LoRaWAN frame counter (idempotency; null from the real HTTP device) |
| `rssi` | int null | from device/uplink |
| `snr` | numeric null | from uplink envelope |
| `battery_mv` | int null | optional |
| `device_status` | text null | device's own status (`wet/dry/ok/critical`) — reference only |
| `device_moisture_pct` | numeric null | device's own computed % — reference only |
| `priority` | numeric null | device's `93.5 − 0.6×moisture` — reference only |
| `source` | text not null default 'lorawan' | `lorawan` \| `mock` \| `manual` |

Indexes: `btree(sensor_id, measured_at desc)`; **unique** `(sensor_id, fcnt)` where `fcnt is not null`; fallback dedupe on `(sensor_id, measured_at)`. **Never updated/deleted** — training data. The device's own `moisture_percent/status/priority` are stored for reference but **health is recomputed from `raw`**.

### 2.6 `tree_partnerships` — the M:N relationship + per‑tree streak
| Column | Type | Notes |
|---|---|---|
| `id` | uuid PK | |
| `tree_id` | uuid not null FK→trees | |
| `user_id` | uuid not null FK→profiles | |
| `role` | text not null | `owner` \| `member` \| `caretaker` |
| `active_from` | date not null default current_date | |
| `active_to` | date null | null = open‑ended (owner/member); set for caretaker coverage window |
| `streak` | int not null default 0 | **consecutive healthy days for this tree under this partnership** |
| `streak_frozen` | bool not null default false | true while the owner is on a covered absence |
| `last_eval_date` | date null | last day the cron evaluated this partnership |
| `created_at` | timestamptz default now() | |

Constraints / rules (enforced in FastAPI, see [docs/05](05-scoring-and-gamification.md)):
- A tree may have **at most one active `owner`**.
- `member` rows are created only via **invitation**; `caretaker` rows only via **coverage** of an absence.
- Unique active partnership per `(tree_id, user_id)` (no duplicate roles).
- **Score** for a user = `sum(streak)` over their active partnerships (cached to `profiles.score`).

### 2.7 `absences` — declared unavailability + handoff state
| Column | Type | Notes |
|---|---|---|
| `id` | uuid PK | |
| `user_id` | uuid not null FK→profiles | the absent owner/member |
| `tree_id` | uuid not null FK→trees | which tree they can't tend |
| `partnership_id` | uuid not null FK→tree_partnerships | the partnership being paused |
| `from_date` | date not null | |
| `to_date` | date not null | |
| `status` | text not null default 'open' | `open` (no caretaker yet) \| `covered` \| `expired` |
| `covering_partnership_id` | uuid null FK→tree_partnerships | the caretaker partnership, once taken |
| `created_at` | timestamptz default now() | |

> Retained as **history** even after expiry — it's a key input for the future "where will care lapse" prediction.

### 2.8 `weather_snapshots` — periodic weather capture (history)
| Column | Type | Notes |
|---|---|---|
| `id` | bigserial PK | |
| `captured_at` | timestamptz default now() | |
| `lat` / `lon` | numeric | Karlsruhe centroid by default |
| `temp_c` | numeric null | current |
| `precip_mm` | numeric null | recent/forecast precip |
| `humidity_pct` | numeric null | |
| `forecast_json` | jsonb null | raw Open‑Meteo forecast for later use |

> Written by a scheduled weather fetch. Powers the "heavy‑rain → don't penalize streak" edge case ([docs/05](05-scoring-and-gamification.md) §edge cases) and future prediction.

### 2.9 `notifications` — feed (app `AppNotification`)
| Column | Type | Notes |
|---|---|---|
| `id` | uuid PK | app `id` |
| `user_id` | uuid not null FK→profiles | |
| `kind` | text not null | `thirsty` \| `recovered` \| `coverage_needed` \| `streak_milestone` |
| `title` | text not null | app `title` (generated from kind+tree, e.g. "Berta is thirsty 🌳") |
| `body` | text not null | app `body` |
| `tree_id` | uuid null FK→trees | |
| `payload` | jsonb null | extra data |
| `read` | bool not null default false | app `isRead` |
| `created_at` | timestamptz default now() | app `receivedAt` |

> The demo's push is mocked in the app; persisting a feed here is cheap and serves `AppNotification` 1:1. Build only if time permits.

### 2.10 Deferred / not built (frontend assumptions we deliberately don't back)
- **`watering_events` / liters** — **dropped.** A soil sensor can't measure water *volume*; the app shows the **moisture curve** ([`GET /trees/{id}/readings`](03-api-contract.md) §4) instead of liters. ([docs/08](08-frontend-data-mapping.md) §5)
- **`friendships` / friends leaderboard / user‑level `streak_days`** — **deferred** (social feature, not part of the city‑transparency value). `score` (= Σ per‑tree streaks) is the gamification number.
- **`teams` (named groups)** — a "team" = the set of partnerships on a tree, so no table is needed. If named/invite‑managed teams are wanted later: `teams(id, tree_id, name, created_by)` + `team_members`.

---

## 3. Derived health & score (where computed)

- **`moisture_pct`** = calibrated from the latest reading (FastAPI ingestion).
- **`health_score` (0–100)** = normalized distance of `moisture_pct` to the tree's species optimal band ([docs/05](05-scoring-and-gamification.md) §health).
- **`health_state`** = bucket of moisture vs the species thresholds.
- **`profiles.score`** = Σ active‑partnership `streak`. Recomputed by the daily cron and on streak‑changing events; cached for fast reads.

These caches exist so the app/dashboard get instant reads via Supabase without recomputation.

---

## 4. RLS policy sketch (Supabase direct‑read safety)

The Flutter app does all reads/writes through **FastAPI**; it connects to Supabase **only to subscribe to Realtime** (with the **authenticated** role), so RLS governs which row‑changes it may receive. The React website never touches Supabase. FastAPI uses the **service_role** (bypasses RLS) for all writes and computation.

| Table | authenticated role may | service_role |
|---|---|---|
| `trees` | `SELECT` all (public map data) | full |
| `sensors` | `SELECT` all (status is public) | full |
| `sensor_readings` | `SELECT` all (or last N) | full |
| `profiles` | `SELECT/UPDATE` **own** row (`id = auth.uid()`) | full |
| `tree_partnerships` | `SELECT` rows where `user_id = auth.uid()` **or** tree is public; **no INSERT/UPDATE** | full |
| `absences` | `SELECT` own + open coverage pool; **no INSERT** | full |
| `weather_snapshots` | `SELECT` | full |
| `notifications` | `SELECT/UPDATE` own | full |

> Writes are deliberately blocked for the client so the **no‑competition** and scoring rules can only be applied by FastAPI. Realtime subscriptions inherit the `SELECT` policies.

---

## 5. Enumerations (keep consistent across code & docs)

- `trees.status`: `available`, `adopted`
- `trees.health_state` (ours, 5): `thriving`, `healthy`, `thirsty`, `critical`, `overwatered`
- **app** `HealthState` (4): `healthy`, `warning`, `overmoisturized`, `dead` — mapping in [docs/08](08-frontend-data-mapping.md) §3
- **app** `TreeSpecies` (5): `oak`, `pine`, `birch`, `maple`, `willow` (+ proposed `other`) — mapping in [docs/08](08-frontend-data-mapping.md) §2
- `sensors.status`: `working`, `inactive`, `defect`
- `tree_partnerships.role`: `owner`, `member`, `caretaker`
- `absences.status`: `open`, `covered`, `expired`
- `sensor_readings.source`: `lorawan`, `mock`, `manual`
- `notifications.kind`: `thirsty`, `recovered`, `coverage_needed`, `streak_milestone`

> These are stored as `text` (simplest for the hackathon) but the allowed values are fixed here. Add Postgres `check` constraints if time permits.
