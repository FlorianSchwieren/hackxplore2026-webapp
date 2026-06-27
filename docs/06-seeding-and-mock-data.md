# 06 — Seeding & Mock Data

> How we populate the database so the product looks like a **city‑wide deployment** while keeping the demo deterministic. All seeds must be **idempotent** (re‑runnable) and reproducible (fixed random seed).

## 1. Seed order

```
1. extensions + schema (postgis, tables)         → supabase/migrations/*.sql
2. species_water_profiles                         → seed_species.py
3. trees (all ~130k, from geoportal)              → seed_trees.py
4. resolve trees.species_profile_id               → (inside seed_trees or a step)
5. sensors (mock fleet, inner city) + the 1 real  → seed_sensors.py
6. sensor_readings (current snapshot per sensor)  → seed_readings.py
7. profiles (2 real demo users + ~300 fake)       → seed_users.py
8. tree_partnerships + absences (fake activity)   → seed_partnerships.py
9. demo scenario (User1 + Berta + real sensor)    → seed_demo.py
10. team demo profile (Taylor Team, no JWT)       → seed_team_demo.py
11. funny names + mock health for all trees      → seed_tree_enrichment.py   ← run LAST
```

Provide a single `make seed` / `python -m app.seed all` that runs them in order.

## 2. Trees (`seed_trees.py`)

- **Source:** the geoportal FeatureServer (layer 2). City‑center working copy already saved at [`data/raw/karlsruhe_trees_citycenter.geojson`](../data/raw/karlsruhe_trees_citycenter.geojson) (4,377 trees, Innenstadt‑Ost+West).
- **Full citywide load:** page through all ~130,867 features (the API caps ~2,000/request → use `resultOffset`/`resultRecordCount`, like the script that produced the city‑center file). Request `outFields=objectid,lfdbnr,artdeut,artlat,baumart_allgemein,baumgruppe,stadtteil`, `outSR=4326`, `f=geojson`.
- **Upsert** on `external_id = objectid`. Map geometry → `geom` (`ST_SetSRID(ST_MakePoint(lon,lat),4326)`).
- **Default name:** assigned by `seed_tree_enrichment.py` — deterministic funny names (Heroku-style adjective + tree pun), except **Berta** stays for the demo.
- Resolve `species_profile_id` (see §4).

Endpoint template:
```
https://geoportal.karlsruhe.de/ags04/rest/services/Hosted/Baumkataster/FeatureServer/2/query
  ?where=stadtteil IS NOT NULL
  &outFields=objectid,lfdbnr,artdeut,artlat,baumart_allgemein,baumgruppe,stadtteil
  &returnGeometry=true&outSR=4326&resultOffset=<n>&resultRecordCount=2000&f=geojson
```

> Decision recap: **all trees in the DB** (real citywide stats), but **sensors/users/partnerships only in `Innenstadt-Ost`/`Innenstadt-West`** (dense, manageable demo). No coordinate maths — filter on `stadtteil`.

## 3. Species water profiles (`seed_species.py`)

The dataset has no moisture optima, so we author them. Values below are **reasonable hackathon defaults** (% volumetric‑ish, on our calibrated 0–100 scale), tuned so most street trees sit comfortably and the demo tree can be pushed thirsty then recovered. Refine freely.

### 3.1 Category defaults (`match_kind='category'`, priority 0)
| `match_value` | optimal_min | optimal_max | dry_critical | wet_critical | drought_tolerance |
|---|---|---|---|---|---|
| `Laubbaum` | 30 | 60 | 15 | 80 | medium |
| `Nadelbaum` | 25 | 55 | 12 | 78 | medium |
| `Obstbaum` | 35 | 65 | 18 | 82 | low |
| `Palme` | 20 | 50 | 10 | 75 | high |
| `Topograph. Baum` | 30 | 60 | 15 | 80 | medium |
| `unbekannt` | 30 | 60 | 15 | 80 | medium |
| `default` (fallback) | 30 | 60 | 15 | 80 | medium |

### 3.2 Species overrides (`match_kind='species_lat'`, priority 10)
Cover the inner‑city top species (from the data sample) so the score is genuinely species‑aware:
| `match_value` (artlat startswith) | dt | optimal_min | optimal_max | dry_critical | wet_critical |
|---|---|---|---|---|---|
| `Carpinus betulus` (Hainbuche) | medium | 30 | 60 | 15 | 80 |
| `Acer platanoides` (Spitz‑Ahorn) | medium | 28 | 58 | 14 | 80 |
| `Acer campestre` (Feld‑Ahorn) | high | 22 | 52 | 12 | 78 |
| `Platanus` (Platane) | high | 25 | 55 | 12 | 80 |
| `Aesculus hippocastanum` (Roßkastanie) | low | 35 | 65 | 18 | 82 |
| `Quercus rubra` (Rot‑Eiche) | medium | 28 | 58 | 14 | 80 |
| `Quercus` (Eichen allg.) | high | 25 | 55 | 12 | 80 |
| `Tilia cordata` (Winter‑Linde) | low | 35 | 65 | 18 | 82 |
| `Tilia` (Linden allg.) | low | 33 | 63 | 17 | 82 |
| `Betula pendula` (Sand‑Birke) | low | 35 | 68 | 20 | 84 |
| `Fraxinus excelsior` (Esche) | medium | 30 | 60 | 15 | 80 |
| `Robinia pseudoacacia` (Scheinakazie) | high | 20 | 50 | 10 | 78 |

> Match by `startswith` on `artlat` (cultivars like `Tilia cordata 'Greenspire'` resolve to `Tilia cordata`). Highest `priority` wins; null/`unbekannt` species fall back to category, then `default`.

## 4. Resolving `species_profile_id`
For each tree: try the most specific `species_lat` whose `match_value` is a prefix of `artlat`; else the `category` profile matching `baumart_allgemein`; else `default`. Store the chosen profile id on the tree.

## 5. Sensors (`seed_sensors.py`)

- **Scope:** pick **~1,000 trees in Innenstadt‑Ost/West** at random (fixed seed) and give each a `sensors` row (1:1 with the tree).
- **Status mix** (for the maintenance view): ~92% `working`, ~5% `inactive` (stale `last_seen_at`), ~3% `defect`.
- **IDs:** synthetic `device_ref` = `MOCK-{i:05d}` (the ingestion lookup key) and `device_eui` = `BAUMPATE-MOCK-{i:05d}`. `is_real=false`. Calibration nominal `dry=3099, wet=1500` (example only — [docs/04](04-sensor-and-lorawan.md) §2).
- **The one real sensor:** created in `seed_demo.py` (§8), `is_real=true`, `device_ref='tree_001'`, measured in‑soil calibration.

## 6. Sensor readings (`seed_readings.py`)

- One **current snapshot** reading per mock sensor (static is fine — dashboard is shown briefly). Set both `sensor_id` and the denormalized `tree_id`.
- Distribute `moisture_pct` to produce a believable health distribution, e.g. ~22% thriving, ~54% healthy, ~15% thirsty, ~6% critical, ~3% overwatered (the numbers the dashboard shows). Compute each reading's `raw` back from the chosen pct via the inverse calibration so data is self‑consistent.
- `inactive`/`defect` sensors: old or missing readings.
- `source='mock'`.

## 7. Users & activity (`seed_users.py`, `seed_partnerships.py`)

- **Profiles:** 2 real demo users (see §8) + ~300 fake users with plausible `display_name`s and a spread of `score`s.
- **Partnerships:** assign many inner‑city monitored trees to fake users as `owner` (some with `member` co‑owners) so `partnerships_active`, per‑user scores, and the city `users_total` look real. Set `streak` values consistent with each tree's current health (healthy trees → higher streaks).
- **Absences:** a handful of fake `open`/`covered` absences so the caretaker pool and dashboard `absences_active` aren't empty.
- Recompute `profiles.score = Σ streak` after seeding.

## 8. The demo scenario (`seed_demo.py`) — run LAST, authoritative

This guarantees the 3‑minute spine works regardless of random seeds.
- **User 1** (`alex@baumpate.demo`) and **User 2** (`sam@baumpate.demo`) — real Supabase Auth users, known passwords (in the demo runbook, not committed).
- **Berta** — pick a specific real inner‑city tree (record its `external_id`), set `name='Berta'`, ensure `status='adopted'` with User 1 as `owner`.
- **Real sensor** — `sensors` row, `is_real=true`, Berta's `tree_id`, `device_ref='tree_001'` (what the physical device sends), real in‑soil calibration.
  - **Calibrate in soil, not water** ([docs/04](04-sensor-and-lorawan.md) §2.1): `calibration_dry` = raw in the dry pot before watering, `calibration_wet` = raw in the saturated pot just after. This makes the **watered state land in Berta's healthy band** (≈70–85%) so the avatar turns *happy*, not `overwatered`.
  - Set Berta's species profile generously (e.g. `optimal 40–88`, `wet_critical 92`) as a safety margin so a good watering reads `healthy`.
- **Starting state** — insert a (non‑outlier) reading that puts Berta **below** her healthy band (e.g. `thirsty`, moisture ~22%, raw ~2700) so step 2 shows a sad avatar and step 3's watering visibly recovers her.
- **User 1 streak** — set to a satisfying number (e.g. 12) so the +1 is meaningful.
- Leave User 2 with a couple of nearby trees and `notify_help_opt_in=true` so step 7 (taking over coverage) is natural.

## 9. Demo control scripts (`scripts/`)
- `fake_water.py --tree-id tree_001 --raw 1900` — POST a plausible "just watered" reading to `/ingest/http` (safety net if the ESP32 can't reach the network).
- `make_thirsty.py --tree-id tree_001` — reset Berta to a thirsty reading to re‑run the demo.
- `mock_stream.py` (optional) — periodically jitter a few mock readings for a "living" dashboard.

## 10. Reproducibility rules
- Fixed `random.seed(42)` everywhere mock data is generated.
- Every seed is an **upsert** (safe to re‑run).
- `seed_demo.py` is **idempotent and authoritative** — running it always restores the exact demo starting state. Run it right before pitching.
