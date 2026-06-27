from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlmodel import Session

from app.auth import CurrentUser, require_user
from app.db import get_session
from app.mapping import title_for_tree
from app.schemas import (
    MyTreeOut,
    MyTreesResponse,
    NotificationOut,
    NotificationPatch,
    ProfileOut,
    ProfilePatch,
)

router = APIRouter(tags=["me"])


@router.get("/me", response_model=ProfileOut)
def get_me(
    user: CurrentUser = Depends(require_user),
    session: Session = Depends(get_session),
) -> ProfileOut:
    row = session.execute(
        text(
            """
            select p.*, (
                select count(*) from tree_partnerships tp
                where tp.user_id = p.id and (tp.active_to is null or tp.active_to >= current_date)
            ) as total_trees_count
            from profiles p
            where p.id = :user_id
            """
        ),
        {"user_id": user.id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")
    data = dict(row)
    return ProfileOut(
        id=data["id"],
        display_name=data["display_name"],
        name=data["display_name"],
        email=data.get("email"),
        avatar_url=data.get("avatar_url"),
        score=data["score"],
        notify_help_opt_in=data["notify_help_opt_in"],
        total_trees_count=data["total_trees_count"],
    )


@router.patch("/me", response_model=ProfileOut)
def patch_me(
    payload: ProfilePatch,
    user: CurrentUser = Depends(require_user),
    session: Session = Depends(get_session),
) -> ProfileOut:
    existing = session.execute(
        text("select id from profiles where id = :user_id"),
        {"user_id": user.id},
    ).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Profile not found")
    updates = payload.model_dump(exclude_unset=True)
    if updates:
        set_sql = ", ".join(f"{field} = :{field}" for field in updates)
        session.execute(
            text(f"update profiles set {set_sql} where id = :user_id"),
            {**updates, "user_id": user.id},
        )
        session.commit()
    return get_me(user=user, session=session)


@router.get("/me/trees", response_model=MyTreesResponse)
def get_my_trees(
    user: CurrentUser = Depends(require_user),
    session: Session = Depends(get_session),
) -> MyTreesResponse:
    profile = session.execute(
        text("select score from profiles where id = :user_id"),
        {"user_id": user.id},
    ).mappings().first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    rows = session.execute(
        text(
            """
            select tp.tree_id, t.name, t.external_id, tp.role, tp.streak,
                   st_x(t.geom)::float as lon, st_y(t.geom)::float as lat,
                   t.health_state, t.moisture_pct
            from tree_partnerships tp
            join trees t on t.id = tp.tree_id
            where tp.user_id = :user_id and (tp.active_to is null or tp.active_to >= current_date)
            order by tp.created_at desc
            """
        ),
        {"user_id": user.id},
    ).mappings().all()
    trees = [
        MyTreeOut(
            tree_id=row["tree_id"],
            name=title_for_tree(row["name"], row["external_id"]),
            role=row["role"],
            streak=row["streak"],
            lon=float(row["lon"]),
            lat=float(row["lat"]),
            health_state=row["health_state"],
            moisture_pct=float(row["moisture_pct"]) if row["moisture_pct"] is not None else None,
        )
        for row in rows
    ]
    return MyTreesResponse(
        score=profile["score"],
        longest_streak=max((tree.streak for tree in trees), default=0),
        trees=trees,
    )


@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(
    user: CurrentUser = Depends(require_user),
    session: Session = Depends(get_session),
) -> list[NotificationOut]:
    rows = session.execute(
        text(
            """
            select id, title, body, created_at as received_at, read as is_read
            from notifications
            where user_id = :user_id
            order by created_at desc
            limit 100
            """
        ),
        {"user_id": user.id},
    ).mappings().all()
    return [NotificationOut(**dict(row)) for row in rows]


@router.patch("/notifications/{notification_id}", response_model=NotificationOut)
def mark_notification(
    notification_id: UUID,
    payload: NotificationPatch,
    user: CurrentUser = Depends(require_user),
    session: Session = Depends(get_session),
) -> NotificationOut:
    row = session.execute(
        text(
            """
            update notifications
            set read = :is_read
            where id = :id and user_id = :user_id
            returning id, title, body, created_at as received_at, read as is_read
            """
        ),
        {"is_read": payload.is_read, "id": notification_id, "user_id": user.id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Notification not found")
    session.commit()
    return NotificationOut(**dict(row))
