# 05 — Scoring & Gamification

> The exact rules for health, streaks, score, avatar states, and the edge cases. This is the heart of the citizen experience and must be unambiguous for implementers.

## 1. Health: moisture % → score → state

Every monitored tree has a **species water profile** (`species_water_profiles`, authored — see [docs/06](06-seeding-and-mock-data.md)) with a healthy band `[optimal_min_pct, optimal_max_pct]` and critical edges `dry_critical_pct`, `wet_critical_pct`.

### 1.1 `health_state` (the avatar bucket)
Given the tree's latest `moisture_pct` `m` and its profile:
| Condition | `health_state` | Avatar |
|---|---|---|
| `m < dry_critical_pct` | `critical` | brown, dropping leaves |
| `dry_critical_pct ≤ m < optimal_min_pct` | `thirsty` | yellowing, droopy |
| `optimal_min_pct ≤ m ≤ optimal_max_pct` | `healthy` | green & happy |
| `healthy` **and** streak is high (e.g. ≥ 7) | `thriving` | lush, growing, flowers |
| `m > wet_critical_pct` | `overwatered` | soggy / over‑saturated |

> `thriving` is `healthy` + reward for consistency (streak ≥ threshold), so the avatar visibly "grows" the longer you keep it healthy — matching the mock ("grows when you keep the soil in the right range").

### 1.2 `health_score` (0–100, normalized, species‑aware)
A continuous score for the dashboard and sorting. 100 = centre of the healthy band; decreases toward the edges; 0 at/beyond critical.
```python
def health_score(m, p) -> int:
    centre = (p.optimal_min + p.optimal_max) / 2
    if p.optimal_min <= m <= p.optimal_max:
        half = (p.optimal_max - p.optimal_min) / 2 or 1
        return round(100 - 20 * abs(m - centre) / half)      # 80–100 inside band
    if m < p.optimal_min:                                     # too dry
        span = (p.optimal_min - p.dry_critical) or 1
        return max(0, round(80 * (m - p.dry_critical) / span))
    span = (p.wet_critical - p.optimal_max) or 1             # too wet
    return max(0, round(80 * (p.wet_critical - m) / span))
```
"Healthy band" for streak purposes = `optimal_min ≤ m ≤ optimal_max` (i.e. state `healthy` or `thriving`).

## 2. The streak & score model (LOCKED)

**Each tree partnership has its own streak.** A user's **score is the sum of their partnerships' streaks.**

- `tree_partnerships.streak` = number of **consecutive days** the tree was kept in its healthy band under that partnership.
- `profiles.score = Σ streak` over the user's **active** partnerships (cached; recomputed on change).

### 2.1 Daily evaluation (the cron)
Once per day at a fixed local time (Europe/Berlin, e.g. **20:00**), for every active partnership:
```
healthy_today = tree was in healthy band at the daily snapshot
if partnership.streak_frozen:        # owner on covered absence
    pass                              # do nothing: streak preserved, not incremented
elif healthy_today:
    streak += 1
else:
    streak = 0                        # forgetting a tree wipes its streak
last_eval_date = today
```
Then recompute each affected user's `score = Σ active streaks`.

### 2.2 Worked example (matches the agreed formula)
- 10 trees, each `streak = 100` → `score = 10 × 100 = 1000`.
- Next day: 9 cared for (healthy), 1 forgotten:
  - 9 trees → `streak = 101` each
  - 1 tree → `streak = 0`
  - `score = 9×101 + 0 = 909`  (= `1000 − 100 + 9`) ✓

This makes **forgetting expensive** (you lose the whole accumulated streak of that tree), which is the core incentive to (a) not over‑adopt, and (b) **hand off via absence/coverage** when you can't tend a tree.

### 2.3 Demo immediate‑award path (so step 4 is visible)
We can't wait until 20:00 in a 3‑minute pitch. On ingestion, when a tree **transitions from not‑healthy → healthy** (i.e. the watering moment):
```
if not already counted today and transitioned into healthy band:
    owner_partnership.streak += 1
    recompute owner.score
    (Realtime pushes the change → app shows streak +1 + happy animation)
    mark last_eval_date = today  # so the nightly cron doesn't double-count
```
This is exactly what the nightly cron would have awarded, just early. Guard with `last_eval_date == today` to avoid double counting.

> **Note:** there is a single gamification number — **`score` = Σ per‑tree streaks**. We deliberately do **not** maintain a separate user‑level "streak days" counter (that was a frontend assumption, now deferred). The big number in the app's home screen (e.g. `1001`) is `score`.

## 3. Collaboration mechanics (no competition — INVARIANT)

- **Adopt:** only `available` trees. Adopting flips the tree to `adopted` and creates an `owner` partnership.
- **Invite (team):** an owner can invite a friend → a `member` partnership. Members co‑tend and each build their **own** streak on that tree. (Helping a co‑owned tree is cooperative, never zero‑sum.)
- **Coverage (absence handoff):** the only other way onto an adopted tree.
- **You can never take or "out‑compete" for a tree.** There is no leaderboard that pits neighbours against each other for the same tree; you grow your own score by tending your own trees and by *helping* others.

### 3.1 Absence & streak freezing
- Declaring an absence on a tree sets `streak_frozen = true` on the owner's partnership for `[from,to]`. The owner's streak **neither grows nor breaks** during this window → the holiday doesn't kill the streak.
- When a **caretaker** covers (`POST /coverage`), they get a `caretaker` partnership for `[from,to]` with its **own** streak starting at 0, accruing daily as they keep it healthy → **extra score for helping**.
- On `to_date`: caretaker partnership expires; owner's `streak_frozen` clears and normal evaluation resumes.

### 3.2 Uncovered absence (design decision — flag for review)
If an absence is declared but **no caretaker takes it**:
- **Default rule:** the owner's streak stays **frozen** (protected) for the declared window — declaring the absence is itself the responsible act, and we don't want to punish honesty.
- **Alternative (stronger collaboration pressure):** only freeze if covered; if uncovered and the tree goes critical, the streak breaks. This pushes people to find help.
- **We ship the Default** (freeze on declared absence) for a friendlier demo, but the alternative is a one‑line change. Documented so the team can choose.

## 4. Edge cases (must handle / document)

1. **Heavy rain → `overwatered` is not the user's fault.** If `weather_snapshots` shows significant recent precipitation, an `overwatered` reading must **not** break or penalize the streak (treat as "weather", keep the streak; the avatar may still show soggy but no score loss). The watering "credit" likewise shouldn't be gamed by rain — for the demo this is a documented carve‑out; implement as: *skip streak penalty when precip in last 24h > threshold.*
2. **Sensor goes `inactive`/`defect`:** no readings → don't reset the streak to 0 on missing data; hold the streak (treat unknown as neutral) until data resumes. Only an actual healthy/unhealthy reading moves the streak.
3. **Double counting:** the `last_eval_date == today` guard makes the demo immediate‑award and the nightly cron mutually exclusive per day.
4. **Leaving a tree:** deleting a partnership removes its streak from the user's score; if it was the last partner, the tree returns to `available`.
5. **`thriving` threshold:** keep configurable (default streak ≥ 7) so the avatar's "growth" is tunable for the demo.

## 5. Configuration (one place, env or a `config.py`)
```python
DAILY_EVAL_LOCAL_TIME = "20:00"            # Europe/Berlin
THRIVING_STREAK_THRESHOLD = 7
RAIN_PENALTY_SKIP_PRECIP_MM_24H = 5.0      # heavy-rain carve-out
UNCOVERED_ABSENCE_PROTECTS_STREAK = True   # default rule (§3.2)
```

## 6. What the frontends render from this
- **App homepage:** `score` (the big number, e.g. `1001`) + per‑tree `health_state`.
- **App detail:** avatar from `health_state` (+ `thriving` growth), the tree's `streak`, recent moisture.
- **App, after watering:** realtime `streak +1` and avatar flip to happy — the demo payoff.
- **Dashboard:** `city_health_score` and the health distribution (§docs/03 `/stats/overview`).
