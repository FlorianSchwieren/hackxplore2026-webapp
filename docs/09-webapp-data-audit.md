# 09 — Reporting Website: Data Audit

> Audit of [`hackxplore2026-webapp`](../hackxplore2026-webapp) (the React/Vite city dashboard) against our backend.
>
> **Guiding principle:** the website is an early, *vibe-coded* prototype and makes some wrong assumptions. **It adapts to our clean API — we do not bend the backend to its types.** Our job is only to make sure the backend **provides the data the dashboard genuinely needs**, through clear, model-grounded endpoints. We do **not** add a shadow `/web/*` API or invent fields just to match its current code.

## 1. Decisions baked in (this session)
- **Website reads from FastAPI only** — never Supabase directly. **All computation server-side.** (See [docs/01](01-architecture.md) §3.)
- **The website adapts to our contract** ([docs/03](03-api-contract.md)). We do not replicate its invented column names, its `age_years`, its "one sensor → many trees" model, or a parallel `/web/*` namespace.
- **Sensor ↔ tree is 1:1.** Each adopted tree has its own sensor — that's exactly how we can show per-tree state. The website's `covered_tree_ids[]` (one sensor, many trees) is a wrong assumption; it adapts.
- The deployed site currently runs on **mock data** (verified: no Supabase URL in the built bundle), so nothing real constrains us.

## 2. What the dashboard genuinely needs → the endpoint that serves it
Every real need is already covered by an **existing** endpoint in [docs/03](03-api-contract.md). Only one small addition is required (the history chart).

| Dashboard need (current webapp hook) | Served by (existing endpoint) |
|---|---|
| Tree map with health + location (`useTrees`) | `GET /trees` (bbox, filters → `health_state`, `moisture_pct`, lon/lat, `stadtteil`, `status`) |
| Tree detail panel (`useTreeDetail`) | `GET /trees/{id}` |
| Sensor map + maintenance status (`useSensors`) | `GET /sensors` (`working/inactive/defect`, `last_seen_at`, location via its tree) |
| Moisture history chart (`useTreeReadings`/`useSensorReadings`) | **NEW** `GET /trees/{id}/readings?days=30&limit=90` (the only addition) |
| City stats: totals, health distribution, sensor status, city score (`useNetworkStats`) | `GET /stats/overview` |
| Per-district breakdown | `GET /stats/by-stadtteil` |
| Weather panel (`useWeather`) | `GET /weather/forecast` |
| "Where to intervene" / prediction (`MLRecommendation`) | `GET /predictions` (stub) |

## 3. Website assumptions we explicitly do NOT adopt (it adapts)
- **`covered_tree_ids` / one-sensor-many-trees** → we keep **1:1**; a tree references its own sensor.
- **`age_years`** → **dropped** (not in the Karlsruhe data, no value).
- **`humidity_status` enum** (`dry/low/normal/moist`) → we send **`health_state`** (+ `moisture_pct`); the website maps those to its own colours/labels. We don't maintain a second enum.
- **Its column names** (`tree_type`, `common_name`, `current_humidity`, `district`, `value`, `timestamp`) → the website renames to our fields in its fetch layer.
- **`NetworkStats` 30-day history arrays** → **not core.** `GET /stats/overview` is the current truth; growth-history charts can be added later or mocked on the frontend. We don't build a history-aggregation endpoint for the hackathon.
- **Leaderboard / user ranking** → **not core dashboard data**; deferred (§6).

## 4. Field mapping (what we provide → how the site consumes it)
The site renames on its side; we expose our clean model.

**Tree**
| Website field | Our field | Note |
|---|---|---|
| `id` | `id` | |
| `name` | `name` | |
| `tree_type` | `artlat` | |
| `common_name` | `artdeut` | null → fallback `baumart_allgemein` |
| `current_humidity` | `moisture_pct` | we compute (smoothed) |
| `humidity_status` | derive from `health_state` | site maps; we don't store a 2nd enum |
| `sensor_id` | `sensor_id` | 1:1 |
| `lat`,`lng` | `geom` | |
| `district` | `stadtteil` | |
| `owner_username` | owner partnership `display_name` | null if `available` |
| `created_at` | `created_at` | |
| ~~`age_years`~~ | — | **dropped** |

**Sensor**
| Website field | Our field | Note |
|---|---|---|
| `id` | `id` | |
| `status` (`active/inactive`) | `status` (`working/inactive/defect`) | site collapses to 2 |
| `last_activity` | `last_seen_at` | |
| `lat`,`lng` | its tree's `geom` | sensor sits at its tree (1:1) — no separate coords needed |
| `installed_at`,`created_at` | same | |
| `name`,`model_type`,`battery_level` | optional cosmetic | provide if cheap (generated name + battery from latest reading); not essential |
| ~~`covered_tree_ids`~~ | — | **n/a** under 1:1 — it's just `[the one tree]` |

**SensorReading** (`GET /trees/{id}/readings`)
| Website field | Our field |
|---|---|
| `id` | `id` |
| `sensor_id` | `sensor_id` |
| `tree_id` | the sensor's tree (1:1) |
| `value` | `moisture_pct` |
| `timestamp` | `measured_at` |

## 5. The one genuinely new endpoint
`GET /trees/{id}/readings?days=30&limit=90` → moisture time series for the detail chart. Clean, on the existing resource, not a `/web` mirror. (No separate sensor-readings endpoint needed — 1:1 means tree readings = its sensor's readings.) Added to [docs/03](03-api-contract.md) §4.

## 6. Open (not blockers — defaults chosen)
- **Stats growth-history charts** → default: current-only via `/stats/overview`; add histories later if wanted.
- **Participation/leaderboard view** → default: deferred (not core city-transparency data).

## 7. Verdict
**Yes — the backend provides every piece of data the dashboard genuinely needs**, via existing endpoints plus one readings endpoint. No shadow API, no invented fields, no `age_years`, sensors stay 1:1. The website adapts (renames fields, maps `health_state`→colours). **No endpoints removed.**
