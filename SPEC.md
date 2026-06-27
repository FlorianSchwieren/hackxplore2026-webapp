# Baumpate — Backend Specification (Master)

> **Working product name:** *Baumpate* (from the German civic concept *Baumpatenschaft* — tree sponsorship). Changeable.
> **Challenge:** "Smart Watering for Urban Trees" — VEGA / HackXplore, Karlsruhe.
> **This document is the index.** Detailed specs live in [`/docs`](docs/). Read this first, then follow the read order below.

---

## 1. Elevator pitch

Cities don't know **which** urban trees need water **and when**, so water, money, and citizen goodwill are wasted. *Baumpate* puts a cheap soil‑moisture sensor (ESP32 + capacitive probe) in the ground and turns watering into a **collaborative, gamified civic act**: citizens "adopt" a tree (a *Baumpatenschaft*), keep its soil in a healthy range, and grow a Duolingo‑style streak. Meanwhile the city gets a live **transparency dashboard** over every tree and sensor, **saves money** on blind watering tours, and can **predict** where water shortages will appear next.

## 2. The four value pillars (memorize these — every design decision serves one)

1. **Community collaboration.** Citizens form *Baumpatenschaften*, optionally as teams. The system is **strictly cooperative — never competitive**: you can only ever *help*, never take a tree from someone.
2. **Transparency for the city.** A reporting dashboard shows the live state of all trees and sensors (working / inactive / defect), health distribution, and per‑district breakdowns.
3. **Cost reduction for the city.** Targeted, data‑driven watering means fewer water‑truck tours → lower municipal cost.
4. **Prediction.** From sensor data + weather **and** crowd‑sourced user activity (declared absences, historically), forecast *where and when* water shortages will occur, producing a probability score for "when does the city need to step in." (ML mocked for now; data model is built to support it later — see [docs/07](docs/07-implementation-plan.md).)

## 3. What we are building

**Backend only.** Two frontends are built by other team members and consume our backend:

| Surface | Tech | Built by | Talks to |
|---|---|---|---|
| Citizen app | **Flutter** | other team | Supabase (reads + realtime) + FastAPI (writes/logic) |
| Reporting website | **React** | other team | FastAPI (aggregates) + Supabase (map reads) |
| Sensor | **ESP32 + capacitive soil moisture sensor** | hardware team | FastAPI ingestion endpoint |

Our deliverable is the **backend**: database, ingestion + LoRaWAN/Helium adapter, business logic (partnerships, absences, scoring), aggregates, weather, prediction stub, realtime, and the seed/mock data that makes the whole thing look like a city‑wide deployment.

## 4. The 3‑minute demo (the spine — everything must serve this)

1. **User 1** gets a (frontend‑mocked) push: *"Your tree is thirsty."*
2. User 1 opens the app → sees the tree avatar looking sad (low moisture).
3. User 1 **physically waters the real tree**; the **one real ESP32 sensor** POSTs the new reading over WiFi/HTTPS.
4. Backend detects the tree is back in its **healthy range** → the app updates in **realtime**: happy avatar animation + **streak +1**.
5. User 1 declares an **absence** (away 2 weeks) so the streak is protected.
6. **Switch to the city dashboard (React):** current state of all trees, number of participating users, sensor health, district stats, and the (mocked) forecast of where the city must step in.
7. **Back to the app as User 2:** browses the map, sees a tree that needs a **caretaker** (User 1's absence), takes it over → earns extra score, purely by helping.

> Every tree except the demo tree is **mocked**. Every sensor except the one real device is **mocked**. The realtime watering moment (steps 3–4) and the city‑wide statistics (step 6) are the two things that must look flawless.

## 5. Architecture at a glance

```
   ESP32 (real)  ──HTTP POST raw──►  FastAPI /ingest/http
                                          │ wrap → LoRaWAN/Helium uplink JSON
                                          ▼
                                     FastAPI /ingest/lorawan  (decoder)
                                          │ write reading + recompute health/streak
                                          ▼
   Flutter app  ◄──realtime──  Supabase (Postgres + Realtime + Auth + RLS + PostGIS)
   React dash   ◄──REST aggregates──  FastAPI  ──reads/writes──┘
```

- **Supabase** = Postgres database, **Realtime** (app subscribes to live changes), **Auth** (simple email/password login), **RLS** (row security), **PostGIS** (map/bbox queries).
- **FastAPI** = ingestion + LoRaWAN adapter, all business logic, scoring cron, aggregates, weather proxy, prediction stub. Uses the Supabase **service‑role** key (bypasses RLS) for writes.
- **API boundary (hybrid):** app does **reads + realtime directly against Supabase**; **all writes/logic go through FastAPI**; the React dashboard reads **aggregates from FastAPI**. (See [docs/01](docs/01-architecture.md).)

## 6. Tech stack

- **Language/framework:** Python 3.12 + **FastAPI**
- **Package/deps:** **uv**
- **ORM/models:** **SQLModel** (Pydantic + SQLAlchemy)
- **DB / platform:** **Supabase** (managed Postgres + Realtime + Auth + PostGIS)
- **Migrations:** **Supabase migrations (SQL)** — *not* Alembic, to keep one source of truth with RLS/PostGIS
- **Weather:** **Open‑Meteo** (free, no API key)
- **Demo networking:** FastAPI local + **ngrok** tunnel so the real sensor can reach it
- **ML/prediction:** mocked now; history tables in place for a real model later

## 7. Scope decisions (locked)

- **Trees in DB:** load **all ~130,867 Karlsruhe trees** (one‑time paginated seed) so city‑wide statistics are real. Partition by the existing `stadtteil` field — no coordinate maths needed.
- **Active deployment** (sensors, users, partnerships) is **concentrated in the inner city** (`Innenstadt-Ost` + `Innenstadt-West`, 4,377 trees) so the app/map stays dense and the demo stays manageable. A working subset is already downloaded: [`data/raw/karlsruhe_trees_citycenter.geojson`](data/raw/karlsruhe_trees_citycenter.geojson).
- **Sensor payload:** the ESP32 sends **raw ADC values**; the backend calibrates to moisture %.
- **Species‑aware health:** the dataset has species but **no moisture optima** → we author a `species_water_profiles` lookup (keyed on `baumart_allgemein`, with overrides for ~12 common species). Health score normalized **0–100** per species.
- **Auth:** Supabase Auth with simple user login; 2 real demo users + ~300 seeded fake users.
- **Prediction:** mocked in the frontend now; backend exposes an optional stub + retains history.

## 8. Scoring model (locked — see [docs/05](docs/05-scoring-and-gamification.md))

- Each **tree partnership has its own streak** = consecutive days the tree was kept healthy.
- A user's **score = the sum of all their partnerships' streaks.**
- Daily: tree healthy → its streak `+= 1`; not healthy → streak resets to `0`.
- Worked example: 10 trees @ streak 100 → score 1000. Next day care for 9, forget 1 → `9×101 + 0 = 909`.
- Forgetting a tree is costly → motivates the **absence/caretaker handoff** (protects the streak).

## 9. Document map & read order

| # | Doc | What it covers |
|---|---|---|
| — | **SPEC.md** (this) | Index, decisions, demo spine |
| 00 | [vision-and-value](docs/00-vision-and-value.md) | Problem, solution, 4 pillars, full pitch narrative, jury fit |
| 01 | [architecture](docs/01-architecture.md) | Components, API boundary, data flows, deployment |
| 02 | [data-model](docs/02-data-model.md) | Tables, columns, relationships, RLS |
| 03 | [api-contract](docs/03-api-contract.md) | All endpoints + JSON examples + realtime channels |
| 04 | [sensor-and-lorawan](docs/04-sensor-and-lorawan.md) | Payloads, calibration, Helium/LoRaWAN adapter, mock simulator |
| 05 | [scoring-and-gamification](docs/05-scoring-and-gamification.md) | Streak/score math, avatar states, edge cases |
| 06 | [seeding-and-mock-data](docs/06-seeding-and-mock-data.md) | Seed scripts, species profiles, demo scenario data |
| 07 | [implementation-plan](docs/07-implementation-plan.md) | Phased, step‑by‑step build plan + demo checklist |
| 08 | [frontend-data-mapping](docs/08-frontend-data-mapping.md) | How the backend serves the Flutter app's models (+ gaps/decisions) |
| 09 | [webapp-data-audit](docs/09-webapp-data-audit.md) | Audit: the React reporting website reads our FastAPI endpoints and adapts to our model (we compute everything; no shadow API) |

Agent operating guide: [`CLAUDE.md`](CLAUDE.md) (symlinked as `AGENTS.md`).

## 10. Critical invariants (do not violate)

- **Cooperative only, never competitive.** Adopted trees can never be taken; others join only by **invitation** or by **covering a declared absence**.
- **Backend only.** Do not build UI; expose clean contracts for Flutter + React.
- **Sensor sends raw ADC**; calibration happens in the backend.
- **Score = sum of per‑tree streaks** (not a flat counter).
- **Append‑only history** for sensor readings, weather, and absences (future ML depends on it).
- The **demo spine in §4** trumps everything; if a feature endangers steps 3–4 or 6, cut it.
