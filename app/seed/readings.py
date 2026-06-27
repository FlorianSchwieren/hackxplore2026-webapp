import random
from decimal import Decimal

from sqlalchemy import text
from sqlmodel import Session

from app.calibration import health_score, health_state, pct_to_raw

RANDOM_SEED = 42


def _target_moisture(index: int) -> float:
    bucket = index % 100
    if bucket < 22:
        return random.uniform(42, 56)  # healthy, many will become thriving via partnerships
    if bucket < 76:
        return random.uniform(35, 55)
    if bucket < 91:
        return random.uniform(20, 29)
    if bucket < 97:
        return random.uniform(5, 14)
    return random.uniform(84, 92)


def seed(session: Session) -> int:
    random.seed(RANDOM_SEED)
    rows = session.execute(
        text(
            """
            select s.id as sensor_id, s.tree_id, s.device_ref, s.status,
                   s.calibration_dry, s.calibration_wet,
                   sp.optimal_min_pct, sp.optimal_max_pct, sp.dry_critical_pct, sp.wet_critical_pct
            from sensors s
            join trees t on t.id = s.tree_id
            join species_water_profiles sp on sp.id = t.species_profile_id
            where s.is_real = false
            order by s.device_ref
            """
        )
    ).mappings().all()
    count = 0
    for index, row in enumerate(rows):
        if row["status"] == "defect":
            continue
        moisture = round(_target_moisture(index), 2)
        raw = pct_to_raw(moisture, row["calibration_dry"], row["calibration_wet"])
        measured_expr = "now() - interval '10 days'" if row["status"] == "inactive" else "now()"
        session.execute(
            text(
                f"""
                insert into sensor_readings (
                    sensor_id, tree_id, raw, moisture_pct, measured_at, source
                )
                values (:sensor_id, :tree_id, :raw, :moisture_pct, {measured_expr}, 'mock')
                on conflict do nothing
                """
            ),
            {
                "sensor_id": row["sensor_id"],
                "tree_id": row["tree_id"],
                "raw": raw,
                "moisture_pct": Decimal(str(moisture)),
            },
        )
        profile = type(
            "Profile",
            (),
            {
                "optimal_min_pct": float(row["optimal_min_pct"]),
                "optimal_max_pct": float(row["optimal_max_pct"]),
                "dry_critical_pct": float(row["dry_critical_pct"]),
                "wet_critical_pct": float(row["wet_critical_pct"]),
            },
        )()
        state = health_state(moisture, profile)
        score = health_score(moisture, profile)
        session.execute(
            text(
                """
                update trees
                set moisture_pct = :moisture_pct,
                    health_score = :health_score,
                    health_state = :health_state,
                    last_reading_at = now()
                where id = :tree_id
                """
            ),
            {
                "tree_id": row["tree_id"],
                "moisture_pct": Decimal(str(moisture)),
                "health_score": score,
                "health_state": state,
            },
        )
        count += 1
    session.commit()
    return count
