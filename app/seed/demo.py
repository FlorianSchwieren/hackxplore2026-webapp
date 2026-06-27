from decimal import Decimal

from sqlalchemy import text
from sqlmodel import Session

from app.calibration import health_score, health_state, pct_to_raw
from app.seed.users import DEMO_USER_1_ID, DEMO_USER_2_ID


def _ensure_demo_profile(session: Session) -> str:
    row = session.execute(
        text(
            """
            insert into species_water_profiles (
                match_kind, match_value, optimal_min_pct, optimal_max_pct,
                dry_critical_pct, wet_critical_pct, drought_tolerance, priority, notes
            )
            values ('category', 'demo_berta', 40, 88, 18, 92, 'low', 100, 'Demo tree safety band')
            on conflict (match_value) do update set
                optimal_min_pct = excluded.optimal_min_pct,
                optimal_max_pct = excluded.optimal_max_pct,
                dry_critical_pct = excluded.dry_critical_pct,
                wet_critical_pct = excluded.wet_critical_pct,
                priority = excluded.priority,
                notes = excluded.notes
            returning id
            """
        )
    ).mappings().one()
    return str(row["id"])


def _berta_tree_id(session: Session) -> str:
    existing = session.execute(
        text("select tree_id from sensors where device_ref = 'tree_001'")
    ).mappings().first()
    if existing:
        return str(existing["tree_id"])
    row = session.execute(
        text(
            """
            select t.id
            from trees t
            left join sensors s on s.tree_id = t.id
            where s.id is null and t.stadtteil in ('Innenstadt-Ost', 'Innenstadt-West')
            order by
              case when t.artlat ilike 'Tilia%' then 0 else 1 end,
              t.external_id
            limit 1
            """
        )
    ).mappings().one()
    return str(row["id"])


def seed(session: Session) -> int:
    profile_id = _ensure_demo_profile(session)
    berta_id = _berta_tree_id(session)

    session.execute(
        text(
            """
            update trees
            set name = 'Berta',
                status = 'adopted',
                species_profile_id = :profile_id
            where id = :tree_id
            """
        ),
        {"tree_id": berta_id, "profile_id": profile_id},
    )
    session.execute(
        text(
            """
            insert into sensors (
                device_eui, device_ref, tree_id, status, is_real,
                calibration_dry, calibration_wet, last_seen_at
            )
            values ('BAUMPATE-tree_001', 'tree_001', :tree_id, 'working', true, 3099, 1500, now())
            on conflict (device_ref) do update set
                tree_id = excluded.tree_id,
                status = 'working',
                is_real = true,
                calibration_dry = excluded.calibration_dry,
                calibration_wet = excluded.calibration_wet,
                last_seen_at = now()
            """
        ),
        {"tree_id": berta_id},
    )
    session.execute(
        text(
            """
            insert into tree_partnerships (tree_id, user_id, role, streak)
            values (:tree_id, :user_id, 'owner', 12)
            on conflict do nothing
            """
        ),
        {"tree_id": berta_id, "user_id": DEMO_USER_1_ID},
    )
    session.execute(
        text(
            """
            update tree_partnerships
            set streak = 12, streak_frozen = false, last_eval_date = null, active_to = null
            where tree_id = :tree_id and user_id = :user_id and role = 'owner'
            """
        ),
        {"tree_id": berta_id, "user_id": DEMO_USER_1_ID},
    )

    sam_trees = session.execute(
        text(
            """
            select t.id
            from trees t
            left join tree_partnerships tp on tp.tree_id = t.id and tp.active_to is null
            where tp.id is null and t.id <> :berta_id
              and t.stadtteil in ('Innenstadt-Ost', 'Innenstadt-West')
            order by t.external_id
            limit 2
            """
        ),
        {"berta_id": berta_id},
    ).mappings().all()
    for index, row in enumerate(sam_trees):
        session.execute(
            text(
                """
                insert into tree_partnerships (tree_id, user_id, role, streak)
                values (:tree_id, :user_id, 'owner', :streak)
                on conflict do nothing
                """
            ),
            {"tree_id": row["id"], "user_id": DEMO_USER_2_ID, "streak": 5 + index},
        )
        session.execute(text("update trees set status = 'adopted' where id = :tree_id"), {"tree_id": row["id"]})

    sensor = session.execute(
        text("select id, calibration_dry, calibration_wet from sensors where device_ref = 'tree_001'")
    ).mappings().one()
    start_moisture = 22.0
    raw = pct_to_raw(start_moisture, sensor["calibration_dry"], sensor["calibration_wet"])
    session.execute(
        text(
            """
            insert into sensor_readings (
                sensor_id, tree_id, raw, moisture_pct, measured_at, source
            )
            values (:sensor_id, :tree_id, :raw, :moisture_pct, '2026-06-27T08:00:00Z', 'mock')
            on conflict do nothing
            """
        ),
        {
            "sensor_id": sensor["id"],
            "tree_id": berta_id,
            "raw": raw,
            "moisture_pct": Decimal(str(start_moisture)),
        },
    )
    profile = type(
        "Profile",
        (),
        {
            "optimal_min_pct": 40,
            "optimal_max_pct": 88,
            "dry_critical_pct": 18,
            "wet_critical_pct": 92,
        },
    )()
    session.execute(
        text(
            """
            update trees
            set moisture_pct = :moisture_pct,
                health_score = :health_score,
                health_state = :health_state,
                last_reading_at = '2026-06-27T08:00:00Z'
            where id = :tree_id
            """
        ),
        {
            "tree_id": berta_id,
            "moisture_pct": Decimal(str(start_moisture)),
            "health_score": health_score(start_moisture, profile),
            "health_state": health_state(start_moisture, profile),
        },
    )
    session.execute(
        text(
            """
            update profiles p
            set score = coalesce((
                select sum(tp.streak)
                from tree_partnerships tp
                where tp.user_id = p.id and (tp.active_to is null or tp.active_to >= current_date)
            ), 0)
            where p.id in (:alex, :sam)
            """
        ),
        {"alex": DEMO_USER_1_ID, "sam": DEMO_USER_2_ID},
    )
    session.commit()
    return 1
