from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlmodel import Session

from app.auth import CurrentUser, require_user
from app.db import get_session
from app.mapping import title_for_tree, to_app_health_state, to_app_species
from app.schemas import (
    Coordinates,
    PartnerOut,
    ReadingOut,
    ReadingsResponse,
    SensorOut,
    SpeciesProfileOut,
    TreeDetail,
    TreeListResponse,
    TreeNamePatch,
    TreeSummary,
)

router = APIRouter(prefix="/trees", tags=["trees"])


def _parse_bbox(bbox: str) -> tuple[float, float, float, float]:
    try:
        min_lon, min_lat, max_lon, max_lat = [float(part) for part in bbox.split(",")]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="bbox must be minLon,minLat,maxLon,maxLat") from exc
    if min_lon >= max_lon or min_lat >= max_lat:
        raise HTTPException(status_code=400, detail="bbox bounds are invalid")
    return min_lon, min_lat, max_lon, max_lat


def _tree_summary(row: dict) -> TreeSummary:
    name = row.get("name")
    external_id = int(row["external_id"])
    lat = float(row["lat"])
    lon = float(row["lon"])
    health = row.get("health_state")
    return TreeSummary(
        id=row["id"],
        external_id=external_id,
        name=name,
        title=title_for_tree(name, external_id),
        artdeut=row.get("artdeut"),
        artlat=row.get("artlat"),
        baumart_allgemein=row["baumart_allgemein"],
        species_app=to_app_species(row.get("artlat"), row.get("baumart_allgemein")),
        stadtteil=row["stadtteil"],
        lon=lon,
        lat=lat,
        coordinates=Coordinates(lat=lat, lng=lon),
        status=row["status"],
        monitored=bool(row.get("monitored")),
        moisture_pct=float(row["moisture_pct"]) if row.get("moisture_pct") is not None else None,
        health_score=row.get("health_score"),
        health_state=health,
        health_state_app=to_app_health_state(health),
        last_reading_at=row.get("last_reading_at"),
        owner_ids=list(row.get("owner_ids") or []),
    )


def _tree_query(where_sql: str) -> str:
    return f"""
        select
            t.id, t.external_id, t.lfdbnr, t.artdeut, t.artlat, t.baumart_allgemein,
            t.baumgruppe, t.stadtteil, t.name, t.status, t.moisture_pct, t.health_score,
            t.health_state, t.last_reading_at, st_x(t.geom)::float as lon, st_y(t.geom)::float as lat,
            exists(select 1 from sensors s where s.tree_id = t.id) as monitored,
            coalesce((
                select array_agg(tp.user_id)
                from tree_partnerships tp
                where tp.tree_id = t.id and tp.role = 'owner' and tp.active_to is null
            ), array[]::uuid[]) as owner_ids
        from trees t
        {where_sql}
    """


def _run_tree_list(
    session: Session,
    bbox: str = Query(...),
    stadtteil: str | None = None,
    status_filter: str | None = None,
    health_state: str | None = None,
    monitored: bool | None = None,
    limit: int = Query(default=1000, le=5000),
) -> TreeListResponse:
    min_lon, min_lat, max_lon, max_lat = _parse_bbox(bbox)
    filters = ["st_intersects(t.geom, st_makeenvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326))"]
    params: dict = {
        "min_lon": min_lon,
        "min_lat": min_lat,
        "max_lon": max_lon,
        "max_lat": max_lat,
        "limit": limit,
    }
    if stadtteil:
        filters.append("t.stadtteil = :stadtteil")
        params["stadtteil"] = stadtteil
    if status_filter:
        filters.append("t.status = :status")
        params["status"] = status_filter
    if health_state:
        filters.append("t.health_state = :health_state")
        params["health_state"] = health_state
    if monitored is not None:
        filters.append(
            "exists(select 1 from sensors s where s.tree_id = t.id)"
            if monitored
            else "not exists(select 1 from sensors s where s.tree_id = t.id)"
        )
    sql = _tree_query("where " + " and ".join(filters)) + " order by t.external_id limit :limit"
    rows = session.execute(text(sql), params).mappings().all()
    trees = [_tree_summary(dict(row)) for row in rows]
    return TreeListResponse(count=len(trees), trees=trees)


@router.get("", response_model=TreeListResponse)
def list_trees(
    bbox: str = Query(...),
    stadtteil: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    health_state: str | None = None,
    monitored: bool | None = None,
    limit: int = Query(default=1000, le=5000),
    _: CurrentUser = Depends(require_user),
    session: Session = Depends(get_session),
) -> TreeListResponse:
    return _run_tree_list(
        session=session,
        bbox=bbox,
        stadtteil=stadtteil,
        status_filter=status_filter,
        health_state=health_state,
        monitored=monitored,
        limit=limit,
    )


@router.get("/available", response_model=TreeListResponse)
def list_available_trees(
    bbox: str = Query(...),
    limit: int = Query(default=1000, le=5000),
    _: CurrentUser = Depends(require_user),
    session: Session = Depends(get_session),
) -> TreeListResponse:
    return _run_tree_list(
        session=session,
        bbox=bbox,
        status_filter="available",
        limit=limit,
    )


@router.get("/{tree_id}", response_model=TreeDetail)
def get_tree(
    tree_id: UUID,
    _: CurrentUser = Depends(require_user),
    session: Session = Depends(get_session),
) -> TreeDetail:
    row = session.execute(
        text(_tree_query("where t.id = :tree_id")),
        {"tree_id": tree_id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Tree not found")
    summary = _tree_summary(dict(row))

    species_row = session.execute(
        text(
            """
            select sp.optimal_min_pct, sp.optimal_max_pct, sp.dry_critical_pct, sp.wet_critical_pct
            from trees t
            join species_water_profiles sp on sp.id = t.species_profile_id
            where t.id = :tree_id
            """
        ),
        {"tree_id": tree_id},
    ).mappings().first()
    sensor_row = session.execute(
        text(
            """
            select id, device_eui, status, is_real, last_seen_at
            from sensors
            where tree_id = :tree_id
            """
        ),
        {"tree_id": tree_id},
    ).mappings().first()
    partners = session.execute(
        text(
            """
            select tp.user_id, p.display_name, tp.role, tp.streak
            from tree_partnerships tp
            join profiles p on p.id = tp.user_id
            where tp.tree_id = :tree_id and (tp.active_to is null or tp.active_to >= current_date)
            order by tp.role, p.display_name
            """
        ),
        {"tree_id": tree_id},
    ).mappings().all()
    readings = session.execute(
        text(
            """
            select id, sensor_id, measured_at, moisture_pct, raw, is_outlier
            from sensor_readings
            where tree_id = :tree_id
            order by measured_at desc
            limit 10
            """
        ),
        {"tree_id": tree_id},
    ).mappings().all()

    return TreeDetail(
        **summary.model_dump(),
        species_profile=SpeciesProfileOut(
            optimal_min_pct=float(species_row["optimal_min_pct"]),
            optimal_max_pct=float(species_row["optimal_max_pct"]),
            dry_critical_pct=float(species_row["dry_critical_pct"]),
            wet_critical_pct=float(species_row["wet_critical_pct"]),
        )
        if species_row
        else None,
        sensor=SensorOut(**dict(sensor_row)) if sensor_row else None,
        partners=[PartnerOut(**dict(row)) for row in partners],
        recent_readings=[
            ReadingOut(
                **{
                    **dict(row),
                    "moisture_pct": float(row["moisture_pct"]),
                }
            )
            for row in readings
        ],
    )


@router.get("/{tree_id}/readings", response_model=ReadingsResponse)
def get_tree_readings(
    tree_id: UUID,
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=90, ge=1, le=1000),
    _: CurrentUser = Depends(require_user),
    session: Session = Depends(get_session),
) -> ReadingsResponse:
    since = datetime.now(UTC) - timedelta(days=days)
    rows = session.execute(
        text(
            """
            select id, sensor_id, measured_at, moisture_pct, raw, is_outlier
            from sensor_readings
            where tree_id = :tree_id and measured_at >= :since
            order by measured_at asc
            limit :limit
            """
        ),
        {"tree_id": tree_id, "since": since, "limit": limit},
    ).mappings().all()
    return ReadingsResponse(
        tree_id=tree_id,
        readings=[
            ReadingOut(
                **{
                    **dict(row),
                    "moisture_pct": float(row["moisture_pct"]),
                }
            )
            for row in rows
        ],
    )


@router.patch("/{tree_id}/name", response_model=TreeSummary)
def rename_tree(
    tree_id: UUID,
    payload: TreeNamePatch,
    user: CurrentUser = Depends(require_user),
    session: Session = Depends(get_session),
) -> TreeSummary:
    allowed = session.execute(
        text(
            """
            select 1 from tree_partnerships
            where tree_id = :tree_id and user_id = :user_id
              and (active_to is null or active_to >= current_date)
            """
        ),
        {"tree_id": tree_id, "user_id": user.id},
    ).first()
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a tree partner")
    session.execute(
        text("update trees set name = :name where id = :tree_id"),
        {"name": payload.name, "tree_id": tree_id},
    )
    session.commit()
    row = session.execute(text(_tree_query("where t.id = :tree_id")), {"tree_id": tree_id}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Tree not found")
    return _tree_summary(dict(row))
