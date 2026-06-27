import base64
from datetime import UTC, datetime
from typing import Any


def _battery_mv(payload: dict[str, Any]) -> int:
    if payload.get("battery_mv") is not None:
        return int(payload["battery_mv"])
    voltage = payload.get("battery_voltage")
    if voltage is None:
        return 0
    return int(float(voltage) * 1000)


def encode_uplink(payload: dict[str, Any], fcnt: int | None = None) -> dict[str, Any]:
    device_ref = str(payload["tree_id"])
    raw = int(payload["raw_value"])
    battery_mv = _battery_mv(payload)
    body = raw.to_bytes(2, "big") + battery_mv.to_bytes(2, "big") + bytes([1, 0])
    measured_at = payload.get("created_at")
    if isinstance(measured_at, datetime):
        measured_at = measured_at.astimezone(UTC).isoformat()

    return {
        "deviceInfo": {
            "devEui": f"BAUMPATE-{device_ref}",
            "deviceName": f"baumpate-{device_ref}",
        },
        "fPort": 10,
        "fCnt": fcnt,
        "data": base64.b64encode(body).decode("ascii"),
        "rxInfo": [
            {
                "rssi": payload.get("rssi"),
                "snr": payload.get("snr"),
                "gatewayId": "mock-gw-01",
            }
        ],
        "time": measured_at or datetime.now(UTC).isoformat(),
        "deviceFields": {
            "status": payload.get("status"),
            "moisture_percent": payload.get("moisture_percent"),
            "priority": payload.get("priority"),
        },
    }


def decode_uplink(env: dict[str, Any]) -> dict[str, Any]:
    payload = base64.b64decode(env["data"])
    if len(payload) < 6:
        raise ValueError("LoRaWAN payload must be at least 6 bytes")
    device_info = env.get("deviceInfo") or {}
    dev_eui = device_info.get("devEui") or ""
    device_ref = dev_eui.removeprefix("BAUMPATE-")
    rx_info = (env.get("rxInfo") or [{}])[0] or {}
    device_fields = env.get("deviceFields") or {}

    return {
        "device_ref": device_ref,
        "fcnt": env.get("fCnt"),
        "rssi": rx_info.get("rssi"),
        "snr": rx_info.get("snr"),
        "raw": int.from_bytes(payload[0:2], "big"),
        "battery_mv": int.from_bytes(payload[2:4], "big") or None,
        "version": payload[4],
        "flags": payload[5],
        "measured_at": env.get("time"),
        "device_status": device_fields.get("status"),
        "device_moisture_pct": device_fields.get("moisture_percent"),
        "priority": device_fields.get("priority"),
    }
