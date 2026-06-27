from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlmodel import Session

from app.auth import CurrentUser, require_user
from app.db import get_session
from app.mapping import title_for_tree, to_app_health_state
from app.schemas import (
    CoPartnerAllTreeOut,
    CoPartnerOut,
    CoPartnerSharedTreeOut,
    CoPartnersResponse,
    MyTreeOut,
    MyTreesResponse,
    NotificationOut,
    NotificationPatch,
    PartnershipNetworkEdge,
    PartnershipNetworkResponse,
    PartnershipNetworkTree,
    PartnershipNetworkUser,
    ProfileOut,
    ProfilePatch,
)

router = APIRouter(tags=["me"])


def _tree_health_fields(row: dict) -> dict:
    health = row.get("health_state")
    moisture = row.get("moisture_pct")
    return {
        "moisture_pct": float(moisture) if moisture is not None else None,
        "health_state": health,
        "health_state_app": to_app_health_state(health),
    }


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


@router.get("/me/co-partners", response_model=CoPartnersResponse, response_model_exclude_none=True)
def get_co_partners(
    include_all_trees: bool = Query(default=False, description="Include every tree each co-partner tends"),
    user: CurrentUser = Depends(require_user),
    session: Session = Depends(get_session),
) -> CoPartnersResponse:
    rows = session.execute(
        text(
            """
            select p.id as user_id, p.display_name, p.avatar_url,
                   tp1.tree_id, t.name, t.external_id,
                   t.moisture_pct, t.health_state,
                   tp1.role as your_role, tp2.role as their_role
            from tree_partnerships tp1
            join tree_partnerships tp2
              on tp1.tree_id = tp2.tree_id
             and tp2.user_id <> tp1.user_id
             and (tp2.active_to is null or tp2.active_to >= current_date)
            join profiles p on p.id = tp2.user_id
            join trees t on t.id = tp1.tree_id
            where tp1.user_id = :user_id
              and (tp1.active_to is null or tp1.active_to >= current_date)
            order by p.display_name, t.external_id
            """
        ),
        {"user_id": user.id},
    ).mappings().all()

    grouped: dict[str, CoPartnerOut] = {}
    for row in rows:
        partner_id = str(row["user_id"])
        if partner_id not in grouped:
            grouped[partner_id] = CoPartnerOut(
                user_id=row["user_id"],
                display_name=row["display_name"],
                avatar_url=row.get("avatar_url"),
                shared_trees=0,
                trees=[],
            )
        partner = grouped[partner_id]
        partner.trees.append(
            CoPartnerSharedTreeOut(
                tree_id=row["tree_id"],
                name=title_for_tree(row["name"], row["external_id"]),
                your_role=row["your_role"],
                their_role=row["their_role"],
                **_tree_health_fields(dict(row)),
            )
        )
        partner.shared_trees = len(partner.trees)

    if include_all_trees and grouped:
        all_rows = session.execute(
            text(
                """
                with co_partner_ids as (
                    select distinct tp2.user_id as id
                    from tree_partnerships tp1
                    join tree_partnerships tp2
                      on tp1.tree_id = tp2.tree_id
                     and tp2.user_id <> tp1.user_id
                     and (tp2.active_to is null or tp2.active_to >= current_date)
                    where tp1.user_id = :user_id
                      and (tp1.active_to is null or tp1.active_to >= current_date)
                )
                select cp.id as user_id, tp.tree_id, t.name, t.external_id,
                       t.moisture_pct, t.health_state,
                       tp.role as their_role, mp.role as your_role
                from co_partner_ids cp
                join tree_partnerships tp
                  on tp.user_id = cp.id
                 and (tp.active_to is null or tp.active_to >= current_date)
                join trees t on t.id = tp.tree_id
                left join tree_partnerships mp
                  on mp.tree_id = tp.tree_id
                 and mp.user_id = :user_id
                 and (mp.active_to is null or mp.active_to >= current_date)
                order by cp.id, t.external_id
                """
            ),
            {"user_id": user.id},
        ).mappings().all()
        all_by_partner: dict[str, list[CoPartnerAllTreeOut]] = {partner_id: [] for partner_id in grouped}
        for row in all_rows:
            partner_id = str(row["user_id"])
            if partner_id not in all_by_partner:
                continue
            your_role = row["your_role"]
            all_by_partner[partner_id].append(
                CoPartnerAllTreeOut(
                    tree_id=row["tree_id"],
                    name=title_for_tree(row["name"], row["external_id"]),
                    their_role=row["their_role"],
                    shared=your_role is not None,
                    your_role=your_role,
                    **_tree_health_fields(dict(row)),
                )
            )
        for partner_id, partner in grouped.items():
            partner.all_trees = all_by_partner.get(partner_id, [])

    co_partners = sorted(
        grouped.values(),
        key=lambda partner: (-partner.shared_trees, partner.display_name.lower()),
    )
    return CoPartnersResponse(count=len(co_partners), co_partners=co_partners)


@router.get("/me/partnership-network", response_model=PartnershipNetworkResponse)
def get_partnership_network(
    max_entities: int = Query(default=200, ge=50, le=200),
    max_users_per_depth: int = Query(default=20, ge=1, le=50),
    user: CurrentUser = Depends(require_user),
    session: Session = Depends(get_session),
) -> PartnershipNetworkResponse:
    max_depth = 3
    user_depth: dict[UUID, int] = {user.id: 0}
    tree_depth: dict[UUID, int] = {}

    frontier_users = [user.id]
    for depth in range(max_depth + 1):
        tree_rows_for_depth = session.execute(
            text(
                """
                select distinct tree_id
                from tree_partnerships
                where user_id = any(:user_ids)
                  and (active_to is null or active_to >= current_date)
                order by tree_id
                """
            ),
            {"user_ids": frontier_users},
        ).mappings().all()
        current_tree_ids = [row["tree_id"] for row in tree_rows_for_depth]
        for tree_id in current_tree_ids:
            tree_depth.setdefault(tree_id, depth)

        if depth == max_depth or not current_tree_ids:
            break

        user_rows_for_next_depth = session.execute(
            text(
                """
                select distinct user_id
                from tree_partnerships
                where tree_id = any(:tree_ids)
                  and not (user_id = any(:known_user_ids))
                  and (active_to is null or active_to >= current_date)
                order by user_id
                limit :limit
                """
            ),
            {
                "tree_ids": current_tree_ids,
                "known_user_ids": list(user_depth),
                "limit": max_users_per_depth,
            },
        ).mappings().all()
        frontier_users = [row["user_id"] for row in user_rows_for_next_depth]
        for user_id in frontier_users:
            user_depth.setdefault(user_id, depth + 1)

    def build_partnership_rows() -> list[dict]:
        if not user_depth or not tree_depth:
            return []
        return [
            dict(row)
            for row in session.execute(
                text(
                    """
                    select user_id, tree_id, role
                    from tree_partnerships
                    where user_id = any(:user_ids)
                      and tree_id = any(:tree_ids)
                      and (active_to is null or active_to >= current_date)
                    order by user_id, tree_id, role
                    """
                ),
                {"user_ids": list(user_depth), "tree_ids": list(tree_depth)},
            ).mappings().all()
        ]

    partnership_rows = build_partnership_rows()
    entity_count = len(user_depth) + len(tree_depth) + len(partnership_rows)
    truncated = entity_count > max_entities
    while entity_count > max_entities and any(depth > 0 for depth in user_depth.values()):
        deepest_depth = max(user_depth.values())
        removable_users = sorted(
            [user_id for user_id, depth in user_depth.items() if depth == deepest_depth],
            key=str,
        )
        if not removable_users:
            break
        user_depth.pop(removable_users[-1], None)

        active_user_ids = list(user_depth)
        tree_rows = session.execute(
            text(
                """
                select distinct tree_id
                from tree_partnerships
                where user_id = any(:user_ids)
                  and (active_to is null or active_to >= current_date)
                """
            ),
            {"user_ids": active_user_ids},
        ).mappings().all()
        active_tree_ids = {row["tree_id"] for row in tree_rows}
        tree_depth = {tree_id: depth for tree_id, depth in tree_depth.items() if tree_id in active_tree_ids}
        partnership_rows = build_partnership_rows()
        entity_count = len(user_depth) + len(tree_depth) + len(partnership_rows)

    user_ids = list(user_depth)
    tree_ids = list(tree_depth)
    if not user_ids or not tree_ids:
        return PartnershipNetworkResponse(
            root_user_id=user.id,
            max_depth=max_depth,
            entity_count=len(user_ids) + len(tree_ids),
            users=[],
            trees=[],
            partnerships=[],
        )

    users_by_id = {
        row["id"]: row
        for row in session.execute(
            text(
                """
                select id, display_name, avatar_url
                from profiles
                where id = any(:user_ids)
                """
            ),
            {"user_ids": user_ids},
        ).mappings().all()
    }
    tree_rows = session.execute(
        text(
            """
            select id, external_id, name, moisture_pct, health_state
            from trees
            where id = any(:tree_ids)
            """
        ),
        {"tree_ids": tree_ids},
    ).mappings().all()
    trees_by_id = {row["id"]: row for row in tree_rows}

    users = [
        PartnershipNetworkUser(
            user_id=user_id,
            display_name=users_by_id[user_id]["display_name"],
            avatar_url=users_by_id[user_id].get("avatar_url"),
            depth=depth,
        )
        for user_id, depth in sorted(user_depth.items(), key=lambda item: (item[1], str(item[0])))
        if user_id in users_by_id
    ]
    trees = [
        PartnershipNetworkTree(
            tree_id=tree_id,
            name=title_for_tree(trees_by_id[tree_id]["name"], trees_by_id[tree_id]["external_id"]),
            depth=depth,
            **_tree_health_fields(dict(trees_by_id[tree_id])),
        )
        for tree_id, depth in sorted(tree_depth.items(), key=lambda item: (item[1], str(item[0])))
        if tree_id in trees_by_id
    ]
    partnerships = [
        PartnershipNetworkEdge(
            user_id=row["user_id"],
            tree_id=row["tree_id"],
            role=row["role"],
            depth=max(user_depth.get(row["user_id"], 0), tree_depth.get(row["tree_id"], 0)),
        )
        for row in partnership_rows
        if row["user_id"] in user_depth and row["tree_id"] in tree_depth
    ]
    return PartnershipNetworkResponse(
        root_user_id=user.id,
        max_depth=max_depth,
        entity_count=len(users) + len(trees) + len(partnerships),
        truncated=truncated,
        users=users,
        trees=trees,
        partnerships=partnerships,
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
