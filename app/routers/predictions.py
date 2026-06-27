from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlmodel import Session

from app.db import get_session
from app.schemas import PredictionItem, PredictionsResponse, StadtteilTrend

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.get("", response_model=PredictionsResponse)
def predictions(
    bbox: str | None = None,
    horizon_days: int = Query(default=7, ge=1, le=30),
    session: Session = Depends(get_session),
) -> PredictionsResponse:
    filters = ["t.health_state in ('thirsty', 'critical')"]
    params: dict = {"limit": 25}
    if bbox:
        min_lon, min_lat, max_lon, max_lat = [float(part) for part in bbox.split(",")]
        filters.append(
            "st_intersects(t.geom, st_makeenvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326))"
        )
        params.update(min_lon=min_lon, min_lat=min_lat, max_lon=max_lon, max_lat=max_lat)
    rows = session.execute(
        text(
            f"""
            select t.id as tree_id, t.stadtteil, t.health_state, t.moisture_pct,
                   exists(select 1 from absences a
                          where a.tree_id = t.id and a.status in ('open','covered')
                            and a.to_date >= current_date) as owner_absent
            from trees t
            join sensors s on s.tree_id = t.id
            where {' and '.join(filters)}
            order by t.health_score asc nulls first, t.last_reading_at asc nulls first
            limit :limit
            """
        ),
        params,
    ).mappings().all()
    shortage_date = date.today() + timedelta(days=min(horizon_days, 7))
    items = []
    for row in rows:
        base = 0.85 if row["health_state"] == "critical" else 0.62
        if row["owner_absent"]:
            base += 0.1
        items.append(
            PredictionItem(
                tree_id=row["tree_id"],
                stadtteil=row["stadtteil"],
                risk_score=round(min(base, 0.98), 2),
                predicted_shortage_date=shortage_date,
                drivers=[
                    driver
                    for driver in [
                        "dry_sensor" if row["health_state"] in {"thirsty", "critical"} else None,
                        "owner_absent" if row["owner_absent"] else None,
                        "dry_forecast",
                    ]
                    if driver
                ],
            )
        )

    trends = session.execute(
        text(
            """
            select stadtteil, avg(moisture_pct) as avg_humidity_now
            from trees
            where moisture_pct is not null
            group by stadtteil
            order by stadtteil
            """
        )
    ).mappings().all()
    return PredictionsResponse(
        generated_at=datetime.now(UTC),
        horizon_days=horizon_days,
        model="mock-v0",
        items=items,
        stadtteil_trend=[
            StadtteilTrend(
                stadtteil=row["stadtteil"],
                avg_humidity_now=float(row["avg_humidity_now"]) if row["avg_humidity_now"] is not None else None,
                avg_humidity_in_7d=max(float(row["avg_humidity_now"]) - 8, 0)
                if row["avg_humidity_now"] is not None
                else None,
            )
            for row in trends
        ],
    )
