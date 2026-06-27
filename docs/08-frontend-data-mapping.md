# 08 — Frontend Data Mapping (Flutter app models)

> Can the backend serve the Flutter app's data models? **Yes.** This maps each app model to our backend. Two things the app currently assumes are **dropped/deferred** (decided this session): **liters** (a soil sensor can't measure water volume) and the **friends / leaderboard** social feature. The app adapts — it isn't a constraint on the backend.

## TL;DR

| App model | Status |
|---|---|
| `Tree` | ✅ served (with field mapping) |
| `HealthState` (4) | ✅ derived from our `health_state` (5) |
| `TreeSpecies` (5) | ✅ derived from species (+ `other` fallback) |
| `User` | ✅ served (`avatar_url`, `totalTreesCount`) |
| `AppNotification` | ✅ served |
| `WaterRecord` / `liters` / `totalWaterLiters` | ❌ **dropped** → show the moisture curve instead |
| `Friend` / `StreakEntry` / `streakDays` | ⏸️ **deferred** (social feature) |

---

## 1. `Tree { id, title, species, healthState, coordinates, ownerIds, waterHistory }`
| App field | Backend source | Mapping |
|---|---|---|
| `id` | `trees.id` | direct |
| `title` | `trees.name` | rename; default `"Baum #<external_id>"` |
| `species` (`TreeSpecies`) | `trees.artlat`/`baumart_allgemein` | mapped to 5‑value enum + `other`, §2 |
| `healthState` (`HealthState`) | `trees.health_state` | mapped 5→4, §3 |
| `coordinates` (`LatLng`) | `trees.geom` | `{ "lat": …, "lng": … }` |
| `ownerIds: List<String>` | `tree_partnerships` | active `user_id`s for the tree |
| `waterHistory` | — | ❌ **dropped** — instead use the moisture curve `GET /trees/{id}/readings`, §5 |

## 2. `TreeSpecies { oak, pine, birch, maple, willow }` (avatar sprite)
The enum is a **choice of avatar sprite**, not botany. Backend returns a derived `species_app` and **always** the real `artdeut`/`artlat` strings (so the UI can show the true name as text even when the sprite is generic).

| App species | Matches (artlat prefix / category) |
|---|---|
| `oak` | `Quercus*` |
| `maple` | `Acer*` |
| `birch` | `Betula*` |
| `pine` | `Pinus*` / category `Nadelbaum` |
| `willow` | `Salix*` |
| `other` | everything else (Linde/Platane/Hainbuche/Kastanie/…) |

> **Resolved:** the app enum gets an `other` bucket (the inner city is mostly Hainbuche/Linde/Platane/Kastanie — none of the 5). Backend computes `species_app`; the app picks the sprite. No backend decision beyond this mapping.

## 3. `HealthState { healthy, warning, overmoisturized, dead }` ← our 5 states
| App `HealthState` | Our `health_state` |
|---|---|
| `healthy` | `thriving` + `healthy` |
| `warning` | `thirsty` |
| `overmoisturized` | `overwatered` |
| `dead` | `critical` |

API returns **both** `health_state` (our 5) and `health_state_app` (the app's 4) so the app uses its enum with zero conversion.

## 4. `User { id, name, avatarUrl?, score, totalTreesCount }`
| App field | Backend | Notes |
|---|---|---|
| `id` | `profiles.id` | |
| `name` | `profiles.display_name` | |
| `avatarUrl?` | `profiles.avatar_url` | nullable |
| `score` | `profiles.score` | = Σ per‑tree streaks ([docs/05](05-scoring-and-gamification.md)) |
| `totalTreesCount` | derived | count of active partnerships |

> `totalWaterLiters` is **removed** (see §5).

## 5. `WaterRecord { date, liters }` — DROPPED
A **soil‑moisture sensor cannot measure liters poured.** Rather than fake a number, the app shows the **moisture curve** from `GET /trees/{id}/readings` (time series of `moisture_pct`), which directly visualises "it was watered" as a rise. If discrete "watered" markers are ever wanted, the frontend can detect a sharp rise in that same curve — no backend liters needed. Decision: **don't track liters.**

## 6. `Friend` / `StreakEntry` / `streakDays` — PARTIAL
A global **friends graph** and a per-user **streak leaderboard** remain deferred (no `friendships` table, no user-level `streak_days`).

**Co-partners** (users who share at least one active `tree_partnerships` row) are served by **`GET /me/co-partners`**. This is derived from existing partnership data — not a separate social graph. Each item includes profile fields plus the shared trees and both roles (`your_role`, `their_role`). Per-tree partners are also on `GET /trees/{id}` → `partners[]`.

The collaborative core — co-owning via invitation, covering an absence — is fully supported via `tree_partnerships`.

## 7. `AppNotification { id, title, body, receivedAt, isRead }`
Served by `notifications` (`id`, `title`, `body`, `received_at`=`created_at`, `is_read`=`read`). Backend generates `title`/`body` from `kind`+tree. Mostly frontend‑mocked for the demo; the table + `GET /notifications` exist so it's real if wanted.

---

## 8. Net schema additions (small)
1. `profiles.avatar_url text null`
2. `notifications.title`, `notifications.body`
3. Pure mapping helpers `to_app_species()`, `to_app_health_state()` (in `app/mapping.py`)

*(No `watering_events`, no `friendships`, no `streak_days` — dropped/deferred per §§5–6.)*

## 9. Verdict
The backend serves the app's models 1:1 or via a trivial derivation, **except** liters (dropped — moisture curve instead), a global friends graph / leaderboard (deferred), and user-level `streak_days` (deferred). Co-partners on shared trees are covered by `GET /me/co-partners`. Everything the demo needs is covered.
