import binascii

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.auth import require_ingest_secret
from app.db import get_session
from app.lorawan import decode_uplink, encode_uplink
from app.schemas import HttpIngestRequest, IngestResponse, LorawanIngestRequest
from app.services.ingestion import ingest_decoded_reading

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/http", response_model=IngestResponse, status_code=202)
def ingest_http(
    payload: HttpIngestRequest,
    _: None = Depends(require_ingest_secret),
    session: Session = Depends(get_session),
) -> dict:
    envelope = encode_uplink(payload.model_dump(), fcnt=payload.fcnt)
    decoded = decode_uplink(envelope)
    decoded.update(
        {
            "device_status": payload.status,
            "device_moisture_pct": payload.moisture_percent,
            "priority": payload.priority,
        }
    )
    return ingest_decoded_reading(session, decoded, source="manual")


@router.post("/lorawan", response_model=IngestResponse, status_code=202)
def ingest_lorawan(
    envelope: LorawanIngestRequest,
    _: None = Depends(require_ingest_secret),
    session: Session = Depends(get_session),
) -> dict:
    try:
        decoded = decode_uplink(envelope.model_dump())
    except (ValueError, KeyError, binascii.Error) as exc:
        raise HTTPException(status_code=400, detail="Malformed LoRaWAN uplink") from exc
    return ingest_decoded_reading(session, decoded, source="lorawan")
