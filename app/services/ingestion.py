from datetime import UTC, datetime, timedelta
from decimal import Decimal
from statistics import median
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import desc, func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.calibration import health_score, health_state, in_healthy_band, is_outlier_raw, raw_to_pct
from app.config import get_settings
from app.models import Sensor, SensorReading, SpeciesWaterProfile, Tree, TreePartnership
from app.services.scoring import award_immediate_if_needed

HEALTHY_STATES = {"healthy", "thriving"}


def _parse_time(value: str | datetime | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _decimal_or_none(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    return Decimal(str(value))


def _latest_valid_moistures(session: Session, sensor_id: UUID, limit: int) -> list[float]:
    rows = session.exec(
        select(SensorReading.moisture_pct)
        .where(SensorReading.sensor_id == sensor_id, SensorReading.is_outlier == False)  # noqa: E712
        .order_by(desc(SensorReading.measured_at))
        .limit(limit)
    ).all()
    return [float(row) for row in rows]


def _active_tree_streak(session: Session, tree_id: UUID) -> int:
    value = session.exec(
        select(func.coalesce(func.max(TreePartnership.streak), 0)).where(
            TreePartnership.tree_id == tree_id,
            TreePartnership.active_to.is_(None),
        )
    ).one()
    return int(value or 0)


def _debounced_state(
    session: Session,
    sensor_id: UUID,
    profile: SpeciesWaterProfile,
    new_state: str,
    old_state: str | None,
    streak: int,
) -> str:
    settings = get_settings()
    if old_state is None or new_state == old_state or settings.state_debounce_readings <= 1:
        return new_state

    samples = _latest_valid_moistures(
        session,
        sensor_id,
        settings.smoothing_window + settings.state_debounce_readings - 1,
    )
    smoothed_states = []
    for offset in range(settings.state_debounce_readings):
        window = samples[offset : offset + settings.smoothing_window]
        if not window:
            break
        smoothed = round(float(median(window)), 2)
        smoothed_states.append(
            health_state(smoothed, profile, streak, settings.thriving_streak_threshold)
        )

    debounced = len(smoothed_states) >= settings.state_debounce_readings and all(
        state == new_state for state in smoothed_states
    )
    return new_state if debounced else old_state


def _find_duplicate(
    session: Session,
    sensor_id: UUID,
    measured_at: datetime,
    fcnt: int | None,
) -> SensorReading | None:
    settings = get_settings()
    if fcnt is not None:
        existing = session.exec(
            select(SensorReading).where(SensorReading.sensor_id == sensor_id, SensorReading.fcnt == fcnt)
        ).first()
        if existing:
            return existing
    return session.exec(
        select(SensorReading).where(
            SensorReading.sensor_id == sensor_id,
            SensorReading.fcnt.is_(None),
            SensorReading.measured_at
            >= measured_at - timedelta(seconds=settings.ingest_dedupe_window_seconds),
            SensorReading.measured_at
            <= measured_at + timedelta(seconds=settings.ingest_dedupe_window_seconds),
        )
    ).first()


def ingest_decoded_reading(session: Session, decoded: dict, source: str = "lorawan") -> dict:
    settings = get_settings()
    sensor = session.exec(select(Sensor).where(Sensor.device_ref == decoded["device_ref"])).first()
    if not sensor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown sensor device_ref={decoded['device_ref']}",
        )
    tree = session.get(Tree, sensor.tree_id)
    if not tree:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor tree not found")
    if not tree.species_profile_id:
        raise HTTPException(status_code=500, detail="Tree has no species profile")
    profile = session.get(SpeciesWaterProfile, tree.species_profile_id)
    if not profile:
        raise HTTPException(status_code=500, detail="Species profile not found")
    if sensor.calibration_dry == sensor.calibration_wet:
        raise HTTPException(status_code=422, detail="Invalid sensor calibration")

    measured_at = _parse_time(decoded.get("measured_at")).replace(microsecond=0)
    duplicate = _find_duplicate(session, sensor.id, measured_at, decoded.get("fcnt"))
    if duplicate:
        return {
            "accepted": True,
            "reading_id": duplicate.id,
            "moisture_pct": float(duplicate.moisture_pct),
            "health_state": tree.health_state,
            "streak_awarded": False,
            "is_outlier": duplicate.is_outlier,
        }

    raw = int(decoded["raw"])
    try:
        moisture_pct = raw_to_pct(raw, sensor.calibration_dry, sensor.calibration_wet)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    outlier = is_outlier_raw(
        raw,
        sensor.calibration_dry,
        sensor.calibration_wet,
        settings.outlier_raw_margin,
    )

    now = datetime.now(UTC)
    reading = SensorReading(
        sensor_id=sensor.id,
        tree_id=sensor.tree_id,
        raw=raw,
        moisture_pct=Decimal(str(moisture_pct)),
        is_outlier=outlier,
        measured_at=measured_at,
        received_at=now,
        fcnt=decoded.get("fcnt"),
        rssi=decoded.get("rssi"),
        snr=_decimal_or_none(decoded.get("snr")),
        battery_mv=decoded.get("battery_mv"),
        device_status=decoded.get("device_status"),
        device_moisture_pct=_decimal_or_none(decoded.get("device_moisture_pct")),
        priority=_decimal_or_none(decoded.get("priority")),
        source=source,
    )
    session.add(reading)
    sensor.last_seen_at = now
    session.add(sensor)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="Duplicate sensor reading") from exc

    streak_awarded = False
    if not outlier:
        old_state = tree.health_state
        recent_moistures = _latest_valid_moistures(session, sensor.id, settings.smoothing_window)
        smoothed_moisture = round(float(median(recent_moistures)), 2)
        active_streak = _active_tree_streak(session, tree.id)
        candidate_state = health_state(
            smoothed_moisture,
            profile,
            active_streak,
            settings.thriving_streak_threshold,
        )
        new_state = _debounced_state(
            session,
            sensor.id,
            profile,
            candidate_state,
            old_state,
            active_streak,
        )
        old_healthy = (
            tree.moisture_pct is not None and in_healthy_band(float(tree.moisture_pct), profile)
        )
        new_healthy = in_healthy_band(smoothed_moisture, profile)

        tree.moisture_pct = Decimal(str(smoothed_moisture))
        tree.health_score = health_score(smoothed_moisture, profile)
        tree.health_state = new_state
        tree.last_reading_at = measured_at
        session.add(tree)
        streak_awarded = award_immediate_if_needed(session, tree.id, new_healthy and not old_healthy)

    session.commit()
    session.refresh(reading)
    return {
        "accepted": True,
        "reading_id": reading.id,
        "moisture_pct": float(reading.moisture_pct),
        "health_state": tree.health_state,
        "streak_awarded": streak_awarded,
        "is_outlier": outlier,
    }
