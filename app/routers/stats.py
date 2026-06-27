from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlmodel import Session

from app.auth import CurrentUser, require_user
from app.db import get_session
from app.schemas import SensorMaintenanceOut, StadtteilStats, StatsOverview

router = APIRouter(tags=["stats"])


@router.get("/stats/overview", response_model=StatsOverview)
def stats_overview(
    _: CurrentUser = Depends(require_user),
    session: Session = Depends(get_session),
) -> StatsOverview:
    scalar_row = session.execute(
        text(
            """
            select
              (select count(*) from trees) as trees_total,
              (select count(*) from sensors) as trees_monitored,
              (select count(*) from profiles) as users_total,
              (select count(*) from tree_partnerships
                where active_to is null or active_to >= current_date) as partnerships_active,
              (select count(*) from absences
                where status in ('open','covered') and to_date >= current_date) as absences_active
            """
        )
    ).mappings().one()
    health_rows = session.execute(
        text(
            """
            select health_state, count(*) as count
            from trees
            where health_state is not null and exists (select 1 from sensors s where s.tree_id = trees.id)
            group by health_state
            """
        )
    ).mappings().all()
    sensor_rows = session.execute(
        text("select status, count(*) as count from sensors group by status")
    ).mappings().all()
    healthy = sum(row["count"] for row in health_rows if row["health_state"] in {"healthy", "thriving"})
    monitored_with_health = sum(row["count"] for row in health_rows)
    city_health_score = round((healthy / monitored_with_health) * 100) if monitored_with_health else 0
    return StatsOverview(
        trees_total=scalar_row["trees_total"],
        trees_monitored=scalar_row["trees_monitored"],
        users_total=scalar_row["users_total"],
        partnerships_active=scalar_row["partnerships_active"],
        absences_active=scalar_row["absences_active"],
        health_distribution={
            state: next((row["count"] for row in health_rows if row["health_state"] == state), 0)
            for state in ["thriving", "healthy", "thirsty", "critical", "overwatered"]
        },
        sensors={
            state: next((row["count"] for row in sensor_rows if row["status"] == state), 0)
            for state in ["working", "inactive", "defect"]
        },
        city_health_score=city_health_score,
    )


@router.get("/stats/by-stadtteil", response_model=list[StadtteilStats])
def stats_by_stadtteil(
    _: CurrentUser = Depends(require_user),
    session: Session = Depends(get_session),
) -> list[StadtteilStats]:
    rows = session.execute(
        text(
            """
            select
              t.stadtteil,
              count(*) as trees,
              count(s.id) as monitored,
              avg(t.health_score) filter (where s.id is not null) as avg_health_score,
              count(*) filter (where t.health_state in ('thirsty', 'critical')) as needs_water
            from trees t
            left join sensors s on s.tree_id = t.id
            group by t.stadtteil
            order by t.stadtteil
            """
        )
    ).mappings().all()
    return [
        StadtteilStats(
            stadtteil=row["stadtteil"],
            trees=row["trees"],
            monitored=row["monitored"],
            avg_health_score=float(row["avg_health_score"]) if row["avg_health_score"] is not None else None,
            needs_water=row["needs_water"],
        )
        for row in rows
    ]


@router.get("/sensors", response_model=list[SensorMaintenanceOut])
def sensors(
    status: str | None = Query(default=None),
    _: CurrentUser = Depends(require_user),
    session: Session = Depends(get_session),
) -> list[SensorMaintenanceOut]:
    where = "where s.status = :status" if status else ""
    rows = session.execute(
        text(
            f"""
            select s.id, s.device_eui, s.tree_id, s.status, s.last_seen_at,
                   t.stadtteil, st_x(t.geom)::float as lon, st_y(t.geom)::float as lat
            from sensors s
            join trees t on t.id = s.tree_id
            {where}
            order by s.last_seen_at desc nulls last
            limit 5000
            """
        ),
        {"status": status} if status else {},
    ).mappings().all()
    return [SensorMaintenanceOut(**dict(row)) for row in rows]
