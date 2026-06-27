# 04 — Sensor & LoRaWAN / Helium Adapter

> The physical sensor, how raw values become moisture %, and the **honest** way we present this as a Helium/LoRaWAN deployment. Connecting the ESP32 to WiFi is the hardware team's job; **the payload *shape* below is our contract.**
>
> Note: the sample readings we saw were **random test data**. So treat the payload **structure** (`tree_id`, `raw_value`, device‑computed fields, `rssi`…) as real, but every **numeric constant** here (calibration endpoints, thresholds) as a **placeholder to measure on the real probe** — don't hardcode them.

## 1. The real sensor

- **Hardware:** ESP32 + capacitive soil‑moisture sensor (the challenge's mandated stack).
- **Output:** the ESP32 ADC produces a **raw integer** (~0–4095, 12‑bit). The current firmware/middleware *also* emits a computed `moisture_percent`, a `status`, and a `priority` — but **we treat `raw_value` as the source of truth** and recompute moisture ourselves so it's **species‑aware and under our control**. We keep the device's computed fields for reference/debugging.
- **Physics:** capacitive sensors read a **lower raw value when wetter**, higher when dry. Calibration inverts this (`dry > wet`).

Exactly **one** real device exists for the demo (it reports as `tree_id: "tree_001"`). Every other "sensor" is a mock row ([docs/06](06-seeding-and-mock-data.md)).

## 2. Calibration (raw ADC → moisture %)

Linear inverse mapping, clamped 0–100:
```python
def raw_to_pct(raw: int, dry: int, wet: int) -> float:
    # capacitive: dry has the HIGHER raw value
    pct = (dry - raw) / (dry - wet) * 100.0
    return max(0.0, min(100.0, round(pct, 2)))
```

**Example calibration constants** (illustrative — sample was random test data, so **measure on the real probe**): `calibration_dry`≈3099 (0%), `calibration_wet`≈1500 (100%). The mapping is linear regardless; only the two endpoints differ per device.

> Store `calibration_dry`/`calibration_wet` **per sensor**; mocks can use any sensible nominal pair.

### 2.1 ⚠️ Calibrate the demo probe *in soil*, not in water
The device's WET point (≈1500) corresponds to the probe **submerged in water**, so saturated readings hit **~80–100%**. Our species healthy bands are ~30–65% → a freshly **watered** tree would read as **`overwatered`**, which ruins the demo's "happy after watering" moment. Fix one of two ways (do the first):
1. **Re‑calibrate in‑situ** before the demo: set `calibration_dry` = raw in the *dry soil* (pre‑watering), `calibration_wet` = raw in the *saturated soil right after watering*. Then dry soil ≈ 0–25% and watered soil ≈ 70–90%, landing inside Berta's band.
2. Or widen the demo tree's species profile so watered (~85%) is `healthy` and only >90% is `overwatered` (see [docs/06](06-seeding-and-mock-data.md) §8).

## 3. Noise handling & smoothing (light defensive insurance)

Capacitive probes occasionally throw a spurious value (loose contact, electrical noise). Keep this simple — it's just insurance so a stray reading can't flip the avatar mid‑pitch, not a big subsystem.

**Pipeline before computing health:**
1. **Plausibility gate** — reject a reading whose `raw` is outside a sane window, e.g. `raw < (wet - 250)` or `raw > (dry + 250)`. (raw 85, 166, 182… are rejected.) Still store the raw row (history), but mark it `is_outlier=true` and don't let it move `trees.health_*`.
2. **Smoothing** — compute the tree's current moisture as the **median of the last N valid readings** (e.g. N=5) or an EWMA, not the single latest value. This kills the 100%/0% oscillation.
3. **Debounce state changes** — only change `health_state` when the smoothed value has been in the new band for ≥2 valid readings, so the avatar doesn't flicker.
4. The **watering event** for the demo's immediate‑award is detected as a *sustained* rise across the smoothing window into the healthy band — not a lone spike.

> Config (in `app/config.py`): `OUTLIER_RAW_MARGIN=250`, `SMOOTHING_WINDOW=5`, `STATE_DEBOUNCE_READINGS=2`.

## 4. Mapping the device's own fields (kept for reference)
- `status` (device): `critical` (≤~25%), `dry` (~25–50%), `ok` (~50–65%), `wet` (≥~70%). **Not species‑aware** → we override with our `health_state` ([docs/05](05-scoring-and-gamification.md)). Stored as `sensor_readings.device_status`.
- `priority` (device) `= 93.5 − 0.6 × moisture_percent` — a linear "needs‑water" score (high = dry). Redundant with our `health_score`; store as `sensor_readings.priority` if useful for the dashboard, otherwise ignore.
- `moisture_percent` (device) — stored as `sensor_readings.device_moisture_pct` for comparison; **our** `moisture_pct` is recomputed from `raw`.

## 5. Inbound payload — `POST /ingest/http` (real device shape)

The device actually sends (per your sample):
```json
{
  "tree_id": "tree_001",
  "raw_value": 2719,
  "moisture_percent": "23.80",
  "status": "critical",
  "priority": "79.20",
  "battery_voltage": null,
  "rssi": -47,
  "created_at": "2026-06-27T07:00:00.075Z"
}
```
- `tree_id` (**string**, e.g. `"tree_001"`) identifies the device/tree. Mapped to a seeded `sensors` row via `sensors.device_ref` (see [docs/02](02-data-model.md)). The real device maps to Berta's sensor.
- `raw_value` — **required**, the source of truth.
- `moisture_percent`, `status`, `priority` — device‑computed; stored for reference, **not** trusted for health.
- `battery_voltage`, `rssi`, `created_at` — optional metadata; `created_at` → `measured_at` (else server time).
- Auth: `Authorization: Bearer <INGEST_SHARED_SECRET>`.

> No `device_eui` and no LoRaWAN `fCnt` come from this device → idempotency falls back to `(sensor_id, measured_at)` (§7). The LoRaWAN envelope (§6) synthesises a `devEui` from `device_ref` and an incrementing `fCnt` in the adapter.

## 6. The Helium/LoRaWAN narrative (and how we make it real)

You can't turn HTTP into LoRaWAN radio without a gateway — but a real Helium/LoRaWAN device ultimately delivers data to a backend as an **HTTP uplink webhook** with a **base64 `frmpayload`** + radio metadata. We make the claim **truthful** by:
1. A small **binary payload format** for a reading.
2. A **middleware encoder** that wraps the device's HTTP reading into the exact uplink envelope a Helium integration would POST.
3. A **decoder** at `POST /ingest/lorawan` — identical to a production payload decoder.

**Jury statement (honest):** *"Our backend ingests the standard LoRaWAN uplink webhook format. We bridge our ESP32 over WiFi today because we have no Helium gateway on site — but the backend is unchanged the moment a real gateway is plugged in: same envelope, same decoder."*

### 6.1 Binary payload (`frmpayload`, `fPort=10`), 6 bytes big‑endian
| Bytes | Field | Encoding |
|---|---|---|
| 0–1 | `raw` | uint16 (ADC) |
| 2–3 | `battery_mv` | uint16 (0 if null) |
| 4 | `version` | uint8 (=1) |
| 5 | `flags` | uint8 (reserved) |

### 6.2 Uplink envelope — `POST /ingest/lorawan` (ChirpStack/Helium‑style)
```json
{
  "deviceInfo": { "devEui": "BAUMPATE-tree_001", "deviceName": "baumpate-tree_001" },
  "fPort": 10, "fCnt": 412, "data": "Cq8AAAEA",
  "rxInfo": [ { "rssi": -47, "snr": null, "gatewayId": "mock-gw-01" } ],
  "time": "2026-06-27T07:00:00.075Z"
}
```

### 6.3 Decoder
```python
import base64
def decode_uplink(env: dict) -> dict:
    p = base64.b64decode(env["data"])
    return {
        "device_ref": env["deviceInfo"]["devEui"].replace("BAUMPATE-", ""),
        "fcnt": env.get("fCnt"),
        "rssi": (env.get("rxInfo") or [{}])[0].get("rssi"),
        "snr":  (env.get("rxInfo") or [{}])[0].get("snr"),
        "raw": int.from_bytes(p[0:2], "big"),
        "battery_mv": int.from_bytes(p[2:4], "big") or None,
        "measured_at": env.get("time"),
    }
```

## 7. Ingestion pipeline (both entry points converge)

```
ESP32 ──POST /ingest/http {tree_id, raw_value, ...}──► encode_uplink() ──► POST /ingest/lorawan {envelope}
                                                                              │ decode_uplink()
                                                  lookup sensor by device_ref (== tree_id)
                                                                              │
                                   PLAUSIBILITY GATE (reject raw outliers, mark is_outlier)
                                                                              │
                              raw_to_pct(raw, sensor.calibration_*) → reading.moisture_pct
                                                                              │
                        INSERT sensor_readings (store device fields + rssi; idempotent)
                                                                              │
                          SMOOTH last N valid readings → trees.moisture_pct
                          DEBOUNCE → trees.health_state / health_score; trees.last_reading_at
                          UPDATE sensors.last_seen_at
                                                                              │
              if smoothed value transitioned into healthy band → award streak (demo path, docs/05)
                                                                              │
                        (Supabase Realtime pushes trees/partnership change to the app)
```

- **Idempotency:** prefer unique `(sensor_id, fcnt)`; since the real device has no fcnt, fall back to dedupe on `(sensor_id, measured_at)` within a small window.
- **Unknown `tree_id`/`device_ref`:** `404` (sensor must be seeded first).
- **Outliers are stored but inert:** they never move tree health (history/ML keeps them with `is_outlier=true`).

## 8. Mock sensor fleet (the other monitored trees)
- ~1,000 seeded `sensors` in the inner city with synthetic `device_ref`/`device_eui` (`MOCK-0001…`), `is_real=false`, nominal calibration (dry 3099 / wet 1500).
- One **current snapshot** reading each (static is fine — dashboard shown for seconds), distributed to give a realistic health mix; compute `raw` back from the chosen pct via inverse calibration so rows are self‑consistent.
- Some sensors seeded `inactive` (stale `last_seen_at`) and `defect` for the maintenance view.
- Optional `scripts/mock_stream.py` jitters a few readings for a "living" dashboard — not required.

## 9. Demo controls & networking
- **Real path:** ESP32 on venue/hotspot WiFi → ngrok HTTPS URL → `/ingest/http`. Pre‑test on the actual network.
- **Safety net:** `scripts/fake_water.py --tree-id tree_001 --raw 1900` POSTs a *plausible* "just watered" reading (inside the gate, ~watered band) to `/ingest/http` so steps 3–4 fire even if the device can't reach the network. Keep ready.
- Pre‑demo checklist: [docs/07](07-implementation-plan.md) §demo‑day.

## 10. Not our responsibility
- ESP32 firmware, WiFi provisioning, wiring (hardware team).
- A real Helium gateway. We only guarantee the backend speaks the standard uplink format.
