from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlmodel import Session

from app.auth import CurrentUser, require_user
from app.db import get_session
from app.mapping import title_for_tree
from app.schemas import (
    AbsenceCreate,
    AbsenceOut,
    AbsenceResponse,
    CoverageCreate,
    CoverageItem,
    CoverageOpenResponse,
    PartnershipOut,
    PartnershipResponse,
)

router = APIRouter(tags=["absences"])


@router.post("/absences", response_model=AbsenceResponse, status_code=201)
def create_absence(
    payload: AbsenceCreate,
    user: CurrentUser = Depends(require_user),
    session: Session = Depends(get_session),
) -> AbsenceResponse:
    if payload.to_date < payload.from_date:
        raise HTTPException(status_code=400, detail="to_date must be on or after from_date")

    partnership = session.execute(
        text(
            """
            select id from tree_partnerships
            where tree_id = :tree_id and user_id = :user_id
              and role in ('owner', 'member')
              and (active_to is null or active_to >= current_date)
            """
        ),
        {"tree_id": payload.tree_id, "user_id": user.id},
    ).mappings().first()
    if not partnership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No active partnership")

    row = session.execute(
        text(
            """
            insert into absences (user_id, tree_id, partnership_id, from_date, to_date, status)
            values (:user_id, :tree_id, :partnership_id, :from_date, :to_date, 'open')
            returning id, status, from_date, to_date
            """
        ),
        {
            "user_id": user.id,
            "tree_id": payload.tree_id,
            "partnership_id": partnership["id"],
            "from_date": payload.from_date,
            "to_date": payload.to_date,
        },
    ).mappings().one()
    session.execute(
        text("update tree_partnerships set streak_frozen = true where id = :id"),
        {"id": partnership["id"]},
    )
    session.commit()
    return AbsenceResponse(absence=AbsenceOut(**dict(row)))


@router.get("/coverage/open", response_model=CoverageOpenResponse)
def open_coverage(
    bbox: str | None = None,
    _: CurrentUser = Depends(require_user),
    session: Session = Depends(get_session),
) -> CoverageOpenResponse:
    filters = ["a.status = 'open'", "a.to_date >= current_date"]
    params: dict = {}
    if bbox:
        try:
            min_lon, min_lat, max_lon, max_lat = [float(part) for part in bbox.split(",")]
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="bbox must be minLon,minLat,maxLon,maxLat") from exc
        filters.append(
            "st_intersects(t.geom, st_makeenvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326))"
        )
        params.update(min_lon=min_lon, min_lat=min_lat, max_lon=max_lon, max_lat=max_lat)

    rows = session.execute(
        text(
            f"""
            select a.id as absence_id, t.id as tree_id, t.name, t.external_id,
                   st_x(t.geom)::float as lon, st_y(t.geom)::float as lat,
                   a.from_date, a.to_date, t.stadtteil, t.health_state
            from absences a
            join trees t on t.id = a.tree_id
            where {' and '.join(filters)}
            order by a.from_date asc
            """
        ),
        params,
    ).mappings().all()
    return CoverageOpenResponse(
        items=[
            CoverageItem(
                absence_id=row["absence_id"],
                tree_id=row["tree_id"],
                name=title_for_tree(row["name"], row["external_id"]),
                lon=float(row["lon"]),
                lat=float(row["lat"]),
                from_date=row["from_date"],
                to_date=row["to_date"],
                stadtteil=row["stadtteil"],
                health_state=row["health_state"],
            )
            for row in rows
        ]
    )


@router.post("/coverage", response_model=PartnershipResponse, status_code=201)
def take_coverage(
    payload: CoverageCreate,
    user: CurrentUser = Depends(require_user),
    session: Session = Depends(get_session),
) -> PartnershipResponse:
    absence = session.execute(
        text("select * from absences where id = :id and status = 'open' for update"),
        {"id": payload.absence_id},
    ).mappings().first()
    if not absence:
        raise HTTPException(status_code=404, detail="Open absence not found")
    if absence["user_id"] == user.id:
        raise HTTPException(status_code=400, detail="You cannot cover your own absence")

    existing = session.execute(
        text(
            """
            select id from tree_partnerships
            where tree_id = :tree_id and user_id = :user_id
              and (active_to is null or active_to >= current_date)
            """
        ),
        {"tree_id": absence["tree_id"], "user_id": user.id},
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already partnered on tree")

    row = session.execute(
        text(
            """
            insert into tree_partnerships (tree_id, user_id, role, active_from, active_to)
            values (:tree_id, :user_id, 'caretaker', :active_from, :active_to)
            returning id, tree_id, user_id, role, streak, active_from, active_to
            """
        ),
        {
            "tree_id": absence["tree_id"],
            "user_id": user.id,
            "active_from": absence["from_date"],
            "active_to": absence["to_date"],
        },
    ).mappings().one()
    session.execute(
        text(
            """
            update absences
            set status = 'covered', covering_partnership_id = :partnership_id
            where id = :absence_id
            """
        ),
        {"partnership_id": row["id"], "absence_id": payload.absence_id},
    )
    session.commit()
    return PartnershipResponse(partnership=PartnershipOut(**dict(row)))
