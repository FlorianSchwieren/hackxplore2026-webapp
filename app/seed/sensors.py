import random

from sqlalchemy import text
from sqlmodel import Session

RANDOM_SEED = 42
DEFAULT_MOCK_SENSOR_COUNT = 1000


def seed(session: Session, count: int = DEFAULT_MOCK_SENSOR_COUNT) -> int:
    random.seed(RANDOM_SEED)
    trees = session.execute(
        text(
            """
            select id
            from trees
            where stadtteil in ('Innenstadt-Ost', 'Innenstadt-West')
            order by external_id
            """
        )
    ).mappings().all()
    if not trees:
        return 0
    selected = random.sample(trees, min(count, len(trees)))
    inserted = 0
    for index, row in enumerate(selected, start=1):
        status_roll = random.random()
        status = "working"
        if status_roll > 0.97:
            status = "defect"
        elif status_roll > 0.92:
            status = "inactive"
        device_ref = f"MOCK-{index:05d}"
        session.execute(
            text(
                """
                insert into sensors (
                    device_eui, device_ref, tree_id, status, is_real,
                    calibration_dry, calibration_wet, last_seen_at
                )
                values (
                    :device_eui, :device_ref, :tree_id, :status, false,
                    3099, 1500,
                    case when :status = 'inactive' then now() - interval '10 days' else now() end
                )
                on conflict (device_ref) do update set
                    tree_id = excluded.tree_id,
                    status = excluded.status,
                    is_real = false,
                    calibration_dry = excluded.calibration_dry,
                    calibration_wet = excluded.calibration_wet,
                    last_seen_at = excluded.last_seen_at
                """
            ),
            {
                "device_eui": f"BAUMPATE-{device_ref}",
                "device_ref": device_ref,
                "tree_id": row["id"],
                "status": status,
            },
        )
        inserted += 1
    session.commit()
    return inserted
