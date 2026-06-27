"""Assign funny names and mock moisture/health to trees missing display data."""

from decimal import Decimal

from sqlalchemy import text
from sqlmodel import Session

from app.calibration import health_score, health_state
from app.seed.funny_names import PRESERVE_TREE_NAMES, funny_tree_name
from app.seed.readings import _target_moisture

MIN_MOCK_HEALTH_SCORE = 12
BATCH_SIZE = 500


def _mock_moisture(external_id: int) -> float:
    moisture = _target_moisture(external_id % 100_000)
    return max(moisture, 8.0)


def assign_funny_names(session: Session) -> int:
    rows = session.execute(
        text("select id, external_id, name from trees order by external_id")
    ).mappings().all()
    updates: list[dict] = []
    for row in rows:
        if row["name"] in PRESERVE_TREE_NAMES:
            continue
        updates.append(
            {
                "id": row["id"],
                "name": funny_tree_name(int(row["external_id"])),
            }
        )
    for start in range(0, len(updates), BATCH_SIZE):
        batch = updates[start : start + BATCH_SIZE]
        session.execute(
            text("update trees set name = :name where id = :id"),
            batch,
        )
    return len(updates)


def assign_mock_health(session: Session) -> int:
    rows = session.execute(
        text(
            """
            select t.id, t.external_id,
                   sp.optimal_min_pct, sp.optimal_max_pct,
                   sp.dry_critical_pct, sp.wet_critical_pct
            from trees t
            join species_water_profiles sp on sp.id = t.species_profile_id
            where t.id not in (select tree_id from sensors where is_real = true)
              and (
                t.moisture_pct is null
                or t.health_score is null
                or t.health_score = 0
              )
            order by t.external_id
            """
        )
    ).mappings().all()
    updates: list[dict] = []
    for row in rows:
        moisture = _mock_moisture(int(row["external_id"]))
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
        updates.append(
            {
                "tree_id": row["id"],
                "moisture_pct": Decimal(str(round(moisture, 2))),
                "health_score": max(health_score(moisture, profile), MIN_MOCK_HEALTH_SCORE),
                "health_state": health_state(moisture, profile),
            }
        )
    for start in range(0, len(updates), BATCH_SIZE):
        batch = updates[start : start + BATCH_SIZE]
        session.execute(
            text(
                """
                update trees
                set moisture_pct = :moisture_pct,
                    health_score = :health_score,
                    health_state = :health_state,
                    last_reading_at = coalesce(last_reading_at, now())
                where id = :tree_id
                """
            ),
            batch,
        )
    return len(updates)


def seed(session: Session) -> int:
    names = assign_funny_names(session)
    health = assign_mock_health(session)
    session.commit()
    return names + health
