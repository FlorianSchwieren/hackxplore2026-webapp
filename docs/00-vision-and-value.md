# 00 — Vision & Value

> Why *Baumpate* exists, who it serves, and the exact story we tell the jury. This is the "north star" doc; when a technical decision is ambiguous, the option that best serves the four pillars and the demo spine wins.

## 1. The problem (from the challenge)

Cities face more frequent heat waves and droughts. Urban trees are especially vulnerable — their roots have limited water‑storage capacity. Municipalities (including the City of Karlsruhe) invest significant resources irrigating public greenery and ask citizens to help water trees. **But the crucial information is missing: which trees actually need water, and when.**

Consequences of guessing:
- Some trees are watered unnecessarily (wasted water + staff time).
- Other trees get too little and suffer.
- Citizen engagement can't be targeted, so goodwill is wasted.

**The challenge is to enable better, data‑driven watering decisions** using an ESP32 + capacitive soil‑moisture sensor.

## 2. The solution in one breath

A cheap sensor reports soil moisture in real time. Citizens **adopt** nearby trees and keep them healthy through a playful app (avatar + streak). The city watches a **live dashboard**, waters only where needed, and **predicts** future shortages. Volunteers and the municipality stop guessing and start coordinating.

## 3. The four value pillars (in depth)

### Pillar 1 — Community collaboration
- Citizens form **Baumpatenschaften** (tree partnerships). Multiple people can care for one tree as a **team**.
- The mechanic is **strictly cooperative**. There is **no competition** for trees:
  - You can adopt only **available** (un‑adopted) trees.
  - You can join an already‑adopted tree **only** by (a) being **invited** by a partner, or (b) **covering** a partner's declared **absence**.
  - You can therefore only ever **help**; you can never take a tree away from someone or "out‑water" them. This is a deliberate anti‑competition design — it prevents conflict and keeps the vibe neighbourly.
- Gamification (Duolingo‑style streaks, see Pillar mechanics in [docs/05](05-scoring-and-gamification.md)) drives habit and retention.

### Pillar 2 — Transparency for the city
- The reporting dashboard (React) gives the municipality a **live, map‑based overview** of every tree: health state, sensor status (working / inactive / defect), district breakdowns, participation numbers.
- This turns an invisible problem ("are our trees OK?") into a monitored, accountable one.

### Pillar 3 — Cost reduction
- Today, water trucks drive routes partly blind. With per‑tree moisture data plus an engaged citizen base handling many trees for free, the city **waters only where the data says it's needed** → fewer truck‑kilometres, less water, less overtime.
- This is the pillar that makes the business case for a municipality to actually buy in.

### Pillar 4 — Prediction
- Short term: combine current sensor readings + weather forecast to flag trees that will dry out soon.
- The differentiator: we **also** have **crowd activity data** — when citizens declare they'll be away (now, and historically). That lets us predict *where care will lapse* and therefore where the **city must step in**, with a probability score and a horizon ("district X, ~5 days").
- Status: the prediction is **mocked in the frontend** for the hackathon. The backend **stores the history** (sensor readings, weather snapshots, absence records) so a genuine model can be trained later without a redesign. See [docs/07](07-implementation-plan.md) §"Later".

## 4. Target groups

- **Engaged citizens** — want a meaningful, low‑effort way to help, with a sense of progress.
- **Cities & municipalities** — want lower cost and defensible, data‑driven decisions.
- **Environmental & climate initiatives** — want measurable local impact and a participation channel.

## 5. The pitch narrative (the 3‑minute spine)

> This is the exact sequence the demo follows. The backend exists to make this sequence real. Numbers in brackets reference the data flows in [docs/01](01-architecture.md) §4.

1. **The hook.** User 1 receives a friendly notification: *"🌳 Your tree Berta is thirsty!"* (notification is **mocked in the app**; timing is choreographed).
2. **The empathy.** User 1 opens the app → the **avatar** of the tree looks droopy / yellowing because its moisture is below the healthy band. [flow: app reads tree health from Supabase]
3. **The action.** User 1 **waters the real tree.** The real ESP32 sensor reads higher moisture and **POSTs** it. [flow: sensor → /ingest/http → LoRaWAN wrap → /ingest/lorawan → reading stored]
4. **The reward (realtime).** Backend sees the tree re‑enter its healthy range → recomputes state → the app **instantly** shows a happy avatar animation and **streak +1**. [flow: Supabase Realtime pushes the change to the app]
5. **The foresight.** User 1 says *"I'll be on holiday for two weeks"* and **declares an absence** so the streak is protected and the tree enters the **caretaker pool**. [flow: app → FastAPI POST /absences]
6. **The city view.** Switch to the **React dashboard**: total trees in Karlsruhe, how many are monitored, how many citizens participate, the health distribution, sensor maintenance status, per‑district stats, and the **forecast** of where the city will likely need to intervene (avg‑humidity trend, mocked). [flow: dashboard → FastAPI /stats/* + /predictions stub]
7. **The collaboration payoff.** Back in the app as **User 2**: the map shows a tree that needs a **caretaker** (User 1's absence). User 2 takes it over → earns extra score **purely by helping** — no competition, just community. [flow: app → FastAPI POST /coverage]

**Close:** "One cheap sensor, a community that cares, and a city that finally knows where to act — *Baumpate* makes urban watering collaborative, transparent, cheaper, and predictable."

## 6. Why this wins on the jury's criteria

| Criterion | How *Baumpate* scores |
|---|---|
| **Innovation & creativity** | Gamified, *strictly cooperative* civic engagement + crowd‑activity‑driven prediction (not just weather). |
| **Practical impact & value** | Direct cost lever for the city (fewer truck tours) + measurable tree health. |
| **Technical feasibility** | Works today with one ESP32 + Supabase + FastAPI; ingests the **standard LoRaWAN uplink format**, so a real Helium gateway is plug‑in. |
| **Scalability** | Already modelled on **all 130k Karlsruhe trees**; `stadtteil` partitioning + PostGIS bbox queries scale the map; mock fleet shows city‑wide rollout. |
| **Pitch quality** | A tight, emotional 3‑minute story with a live realtime moment (steps 3–4). |

## 7. Non‑goals (for the hackathon)

- No production push‑notification infrastructure (FCM/APNs) — notifications are mocked in the app, timed to the demo.
- No trained ML model — prediction is mocked; only the data foundation is built.
- No real Helium hardware — we emulate the uplink format faithfully (see [docs/04](04-sensor-and-lorawan.md)).
- No building of the Flutter/React UIs — we provide the contracts only.
