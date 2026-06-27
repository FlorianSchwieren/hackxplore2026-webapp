# 03 — API Contract

> The HTTP surface the Flutter app and React dashboard build against. FastAPI base path `/api/v1`. JSON in/out, UTF‑8. This is the **contract**: implement it as written so frontends can develop in parallel.

## 1. Conventions

- **Base URL:** `https://<ngrok-host>/api/v1` (demo) — see [docs/01](01-architecture.md) §5.
- **Auth:** user/website endpoints expect `Authorization: Bearer <supabase_jwt>`; FastAPI **verifies it** (HS256 with the Supabase project JWT secret) and derives the user id. Ingestion expects `Authorization: Bearer <INGEST_SHARED_SECRET>`.
- **IDs:** UUID strings unless noted. Tree references accept the internal `id`.
- **Errors:** `{ "error": { "code": "string", "message": "human readable" } }` with appropriate HTTP status (400/401/403/404/409).
- **Time:** ISO‑8601 UTC (`2026-06-27T14:03:00Z`). Dates as `YYYY-MM-DD`.
- **Geo:** `bbox=minLon,minLat,maxLon,maxLat`. Coordinates are WGS84 (lon, lat).
- **Realtime:** live updates are **not** polled here — the app subscribes to Supabase channels (§10).

---

## 2. Health & meta

### `GET /healthz`
→ `200 { "status": "ok", "time": "..." }`

---

## 3. Ingestion (sensor → backend)

### `POST /ingest/http` — raw sensor uplink (what the ESP32 calls)
Auth: `Bearer <INGEST_SHARED_SECRET>`. Real device shape ([docs/04](04-sensor-and-lorawan.md) §5):
```json
// request — raw_value is the source of truth; any device-computed moisture_percent/status/priority are ignored
{ "tree_id": "tree_001", "raw_value": 2480, "battery_voltage": null, "rssi": -47, "created_at": "2026-06-27T14:03:00Z" }
```
Behaviour: look up the sensor by `device_ref` (= `tree_id`), wrap into a LoRaWAN uplink envelope → forward internally to `/ingest/lorawan`. See [docs/04](04-sensor-and-lorawan.md).
→ `202 { "accepted": true, "reading_id": 99123, "moisture_pct": 41.5, "health_state": "healthy", "streak_awarded": true }`

### `POST /ingest/lorawan` — Helium/ChirpStack‑style webhook (the "real" entry)
Auth: `Bearer <INGEST_SHARED_SECRET>`. Accepts the standard uplink envelope (DevEUI, base64 `frmpayload`, `rssi`, `snr`, `fcnt`). Decodes, calibrates, stores, recomputes health, runs the demo immediate‑award. Same response shape as above. (Full schema in [docs/04](04-sensor-and-lorawan.md).)

---

## 4. Trees & map

### `GET /trees`
Query: `bbox` (required for map), `stadtteil?`, `status?` (`available|adopted`), `health_state?`, `monitored?` (bool), `limit?` (default 1000).
→ `200`
```json
{ "count": 312, "trees": [
  { "id": "…", "external_id": 100234, "name": "Berta", "artdeut": "Winter-Linde", "artlat": "Tilia cordata",
    "baumart_allgemein": "Laubbaum", "stadtteil": "Innenstadt-West", "lon": 8.401, "lat": 49.009,
    "status": "adopted", "monitored": true, "moisture_pct": 23.0, "health_score": 38, "health_state": "thirsty",
    "last_reading_at": "2026-06-27T13:50:00Z" } ] }
```

### `GET /trees/{id}` — detail (app detail page + dashboard side panel)
→ `200`
```json
{ "id": "…", "external_id": 100234, "name": "Berta", "artdeut": "Winter-Linde", "artlat": "Tilia cordata",
  "baumart_allgemein": "Laubbaum", "stadtteil": "Innenstadt-West", "lon": 8.401, "lat": 49.009,
  "status": "adopted",
  "species_profile": { "optimal_min_pct": 30, "optimal_max_pct": 60, "dry_critical_pct": 15, "wet_critical_pct": 80 },
  "moisture_pct": 23.0, "health_score": 38, "health_state": "thirsty",
  "sensor": { "device_eui": "70B3…", "status": "working", "is_real": true, "last_seen_at": "…" },
  "partners": [ { "user_id": "…", "display_name": "Alex", "role": "owner", "streak": 12 } ],
  "recent_readings": [ { "measured_at": "…", "moisture_pct": 23.0 } ] }
```

### `GET /trees/available`
Convenience for the tree‑picking screen. Query `bbox`, `limit?`. Returns only `status=available` trees (optionally only monitored).

### `GET /trees/{id}/readings` — moisture time series (detail chart)
Query `days?` (default 30), `limit?` (default 90). Returns the tree's sensor readings (1:1) ordered by time.
→ `200 { "tree_id":"…","readings":[ { "measured_at":"2026-06-27T13:50:00Z","moisture_pct":42.0 } ] }`

---

## 5. Partnerships (adopt / invite / leave)

### `POST /partnerships` — adopt an available tree
Auth: user. Body `{ "tree_id": "…" }`.
- `409` if tree is already `adopted` (enforces no‑competition — can't take a taken tree).
→ `201 { "partnership": { "id":"…","tree_id":"…","user_id":"…","role":"owner","streak":0 } }`

### `GET /me/trees` — homepage map data ("Your Trees")
Auth: user. → `200`
```json
{ "score": 1001, "longest_streak": 100, "trees": [
  { "tree_id":"…","name":"Berta","role":"owner","streak":12,"lon":8.40,"lat":49.00,
    "health_state":"healthy","moisture_pct":42.0 } ] }
```

### `POST /partnerships/{id}/invite` — invite a friend (collaborative team)
Auth: owner of the partnership. Body `{ "email": "friend@…" }` → creates a `member` partnership for that user. (Only way onto an adopted tree besides coverage.)
→ `201 { "partnership": { …, "role":"member" } }`

### `DELETE /partnerships/{id}` — leave a tree
Auth: the partnership's user. If the last partner leaves, tree flips back to `available`.
→ `204`

---

## 6. Absences & coverage (the handoff)

### `POST /absences` — declare I'm away (demo step 5)
Auth: user. Body `{ "tree_id":"…", "from_date":"2026-07-01", "to_date":"2026-07-14" }`.
Behaviour: records absence, **freezes** the owner's streak for that tree, adds tree to the caretaker pool, status `open`.
→ `201 { "absence": { "id":"…","status":"open","from_date":"…","to_date":"…" } }`

### `GET /coverage/open` — trees needing a caretaker (demo step 7)
Auth: user. Query `bbox?`. → `200`
```json
{ "items": [ { "absence_id":"…","tree_id":"…","name":"Berta","lon":8.40,"lat":49.00,
   "from_date":"2026-07-01","to_date":"2026-07-14","stadtteil":"Innenstadt-West","health_state":"healthy" } ] }
```

### `POST /coverage` — take over care during an absence
Auth: user. Body `{ "absence_id":"…" }`.
Behaviour: creates a `caretaker` partnership for `[from,to]`, sets absence `covered`. Caretaker now accrues streak; this is **additive help** — owner keeps their (frozen) streak.
→ `201 { "partnership": { …, "role":"caretaker", "active_from":"…","active_to":"…" } }`

---

## 7. User & score

### `GET /me` → `200 { "id":"…","display_name":"Alex","score":1001,"notify_help_opt_in":true }`
### `PATCH /me` → update `display_name`, `notify_help_opt_in`.
### `PATCH /trees/{id}/name` — name your tree. Body `{ "name":"Berta" }`. Auth: a partner of the tree.

---

## 8. Dashboard (city / reporting site)

### `GET /stats/overview` (demo step 6)
→ `200`
```json
{ "trees_total": 130867, "trees_monitored": 1000, "users_total": 312, "partnerships_active": 540,
  "health_distribution": { "thriving": 220, "healthy": 540, "thirsty": 150, "critical": 60, "overwatered": 30 },
  "sensors": { "working": 920, "inactive": 50, "defect": 30 },
  "city_health_score": 76, "absences_active": 8 }
```
`city_health_score` = % of monitored trees in the healthy band (`healthy`+`thriving`).

### `GET /stats/by-stadtteil`
→ rows `{ "stadtteil":"Innenstadt-West", "trees":3125, "monitored":300, "avg_health_score":71, "needs_water":40 }`.

### `GET /sensors` — maintenance view
Query `status?`. → list of `{ device_eui, tree_id, status, last_seen_at, stadtteil, lon, lat }`.

---

## 9. Weather & prediction

### `GET /weather/forecast`
Proxy/cache of Open‑Meteo for Karlsruhe. → `200 { "current": {…}, "daily": [ { "date":"…","temp_max":31,"precip_mm":0 } ] }`. Also writes a `weather_snapshots` row.

### `GET /predictions` — **stub** (mocked, real contract)
Query `bbox?`, `horizon_days?` (default 7). → `200`
```json
{ "generated_at":"…","horizon_days":7,"model":"mock-v0",
  "items": [ { "tree_id":"…","stadtteil":"Innenstadt-West","risk_score":0.82,
    "predicted_shortage_date":"2026-07-03","drivers":["dry_forecast","owner_absent"] } ],
  "stadtteil_trend": [ { "stadtteil":"Innenstadt-West","avg_humidity_now":34,"avg_humidity_in_7d":22 } ] }
```
> Build the stub so the React forecast panel and "where to intervene" view are real; swap the internals for a model later (see [docs/07](07-implementation-plan.md)). If time is tight, the frontend may mock this entirely — the endpoint is the convenience contract.

---

## 10. Realtime channels (Supabase, app subscribes directly)

The Flutter app subscribes to Supabase Realtime instead of polling:
- **`trees`** — filter on the user's tree ids (or by bbox). Drives the demo step‑4 avatar update (`health_state`, `moisture_pct`, `health_score` change).
- **`tree_partnerships`** — filter `user_id = auth.uid()`. Drives live `streak`/score changes.
- **`sensor_readings`** — optional, for a live moisture chart on the detail page.

Pattern: FastAPI writes the row (service role) → Postgres change → Supabase Realtime pushes to subscribed clients. No extra endpoint needed.

---

## 11. Endpoint summary

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/healthz` | – | liveness |
| POST | `/ingest/http` | secret | raw sensor uplink |
| POST | `/ingest/lorawan` | secret | LoRaWAN/Helium webhook |
| GET | `/trees` | user | map (bbox + filters) |
| GET | `/trees/{id}` | user | detail |
| GET | `/trees/available` | user | tree‑picking |
| GET | `/trees/{id}/readings` | user | moisture time series (chart) |
| PATCH | `/trees/{id}/name` | user | name a tree |
| POST | `/partnerships` | user | adopt |
| GET | `/me/trees` | user | homepage |
| POST | `/partnerships/{id}/invite` | owner | invite friend |
| DELETE | `/partnerships/{id}` | user | leave |
| POST | `/absences` | user | declare absence |
| GET | `/coverage/open` | user | caretaker pool |
| POST | `/coverage` | user | take over care |
| GET/PATCH | `/me` | user | profile |
| GET | `/stats/overview` | user/dash | dashboard totals |
| GET | `/stats/by-stadtteil` | user/dash | per‑district |
| GET | `/sensors` | user/dash | maintenance |
| GET | `/weather/forecast` | – | weather |
| GET | `/predictions` | – | prediction stub |
| GET | `/notifications` | user | `AppNotification[]` |
| PATCH | `/notifications/{id}` | user | mark read |

---

## 12. App‑model (Flutter) compatibility

Endpoints that serve the app's models return **app‑shaped** fields so the colleague needs minimal conversion (full mapping in [docs/08](08-frontend-data-mapping.md)):

- **Tree** responses additionally include: `title` (= name), `species_app` (`oak/pine/birch/maple/willow/other`, derived from species), `health_state_app` (`healthy/warning/overmoisturized/dead`, derived from `health_state`), `coordinates: {lat,lng}`, `owner_ids: string[]`. The real `name`, `artdeut/artlat`, and our `health_state` (5) stay for fidelity.
- **`GET /me`** additionally returns `avatar_url` and `total_trees_count`.

### `GET /notifications` → `[ { "id","title","body","received_at","is_read" } ]`
### `PATCH /notifications/{id}` — body `{ "is_read": true }`

> **Dropped/deferred** (see [docs/08](08-frontend-data-mapping.md) §§5–6): no liters / `watering_events` — a soil sensor can't measure volume, so the app shows the **moisture curve** via `GET /trees/{id}/readings`; no friends/leaderboard endpoints; no user‑level `streak_days` (`score` is the gamification number).

---

## 13. Reporting website (`hackxplore2026-webapp`)

The React dashboard uses **the existing endpoints above** — there is **no `/web/*` shadow API**. The website is an early prototype and **adapts to this contract** (it renames fields and maps `health_state`→colours on its side). Full mapping + the assumptions we deliberately don't adopt: [docs/09](09-webapp-data-audit.md).

What it consumes:
- map + detail → `GET /trees`, `GET /trees/{id}`
- moisture history chart → `GET /trees/{id}/readings` (§4)
- sensor maintenance → `GET /sensors`
- city stats / districts → `GET /stats/overview`, `GET /stats/by-stadtteil`
- weather → `GET /weather/forecast`
- prediction → `GET /predictions`

No new dashboard-specific endpoints, no `age_years`, sensors stay **1:1** with trees.
