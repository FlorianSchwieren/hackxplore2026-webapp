import base64
import binascii

import pytest
from pydantic import ValidationError

from app.lorawan import decode_uplink, encode_uplink
from app.schemas import LorawanIngestRequest


def test_encode_decode_uplink_round_trip() -> None:
    envelope = encode_uplink(
        {
            "tree_id": "tree_001",
            "raw_value": 2480,
            "battery_voltage": 3.7,
            "rssi": -47,
            "created_at": "2026-06-27T07:00:00.075Z",
            "status": "dry",
            "moisture_percent": "23.8",
            "priority": "79.2",
        },
        fcnt=412,
    )
    decoded = decode_uplink(envelope)

    assert decoded["device_ref"] == "tree_001"
    assert decoded["fcnt"] == 412
    assert decoded["raw"] == 2480
    assert decoded["battery_mv"] == 3700
    assert decoded["rssi"] == -47
    assert decoded["device_status"] == "dry"
    assert decoded["device_moisture_pct"] == "23.8"


def test_lorawan_ingest_request_requires_dev_eui() -> None:
    with pytest.raises(ValidationError):
        LorawanIngestRequest.model_validate(
            {
                "deviceInfo": {"deviceName": "baumpate-tree_001"},
                "data": base64.b64encode(b"\x00\x01\x00\x02\x01\x00").decode("ascii"),
            }
        )


def test_lorawan_ingest_request_requires_data() -> None:
    with pytest.raises(ValidationError):
        LorawanIngestRequest.model_validate(
            {
                "deviceInfo": {"devEui": "BAUMPATE-tree_001"},
            }
        )


def test_decode_uplink_rejects_malformed_base64() -> None:
    with pytest.raises(binascii.Error):
        decode_uplink(
            {
                "deviceInfo": {"devEui": "BAUMPATE-tree_001"},
                "data": "not-valid-base64!!!",
            }
        )


def test_decode_uplink_rejects_too_short_payload() -> None:
    with pytest.raises(ValueError, match="at least 6 bytes"):
        decode_uplink(
            {
                "deviceInfo": {"devEui": "BAUMPATE-tree_001"},
                "data": base64.b64encode(b"\x00\x01\x00\x02\x01").decode("ascii"),
            }
        )
