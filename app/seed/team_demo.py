"""Team demo profile: 5 trees, 10 distinct co-partners — used with DEV_AUTH_DISABLED."""

from sqlalchemy import text
from sqlmodel import Session

from app.seed.common import seed_uuid
from app.seed.users import (
    TEAM_DEMO_EMAIL,
    TEAM_DEMO_NAME,
    TEAM_DEMO_USER_ID,
    _upsert_profile,
)

CO_PARTNER_COUNT = 10
TREE_COUNT = 5
MEMBERS_PER_TREE = 2
NEARBY_MIN_METERS = 150
NEARBY_MAX_METERS = 1000

CO_PARTNER_IDS = [seed_uuid(f"user:team-copartner:{index}") for index in range(1, CO_PARTNER_COUNT + 1)]
SECOND_DEGREE_IDS = [seed_uuid(f"user:team-second-degree:{index}") for index in range(1, CO_PARTNER_COUNT + 1)]
THIRD_DEGREE_IDS = [seed_uuid(f"user:team-third-degree:{index}") for index in range(1, CO_PARTNER_COUNT + 1)]
CO_PARTNER_NAMES = [
    "Casey 1",
    "Jordan 2",
    "Riley 3",
    "Quinn 4",
    "Avery 5",
    "Skyler 6",
    "Morgan 7",
    "Jamie 8",
    "Reese 9",
    "Dakota 10",
]
SECOND_DEGREE_NAMES = [
    "Robin 11",
    "Finley 12",
    "Harper 13",
    "Rowan 14",
    "Sage 15",
    "Remy 16",
    "Ellis 17",
    "Kai 18",
    "Blair 19",
    "Toni 20",
]
THIRD_DEGREE_NAMES = [
    "Mika 21",
    "Drew 22",
    "Jules 23",
    "Noel 24",
    "Parker 25",
    "Lane 26",
    "Alexis 27",
    "Briar 28",
    "Kit 29",
    "Arden 30",
]


def _ensure_users(session: Session) -> None:
    _upsert_profile(session, TEAM_DEMO_USER_ID, TEAM_DEMO_NAME, TEAM_DEMO_EMAIL, True)
    for index, partner_id in enumerate(CO_PARTNER_IDS):
        email = f"team-copartner-{index + 1:02d}@baumpate.demo"
        _upsert_profile(session, partner_id, CO_PARTNER_NAMES[index], email, False)
    for index, user_id in enumerate(SECOND_DEGREE_IDS):
        email = f"team-network-{index + 1:02d}@baumpate.demo"
        _upsert_profile(session, user_id, SECOND_DEGREE_NAMES[index], email, False)
    for index, user_id in enumerate(THIRD_DEGREE_IDS):
        email = f"team-network-third-{index + 1:02d}@baumpate.demo"
        _upsert_profile(session, user_id, THIRD_DEGREE_NAMES[index], email, False)


def _owned_tree_ids(session: Session) -> list[str]:
    rows = session.execute(
        text(
            """
            select t.id
            from tree_partnerships tp
            join trees t on t.id = tp.tree_id
            where tp.user_id = :user_id
              and tp.role = 'owner'
              and tp.active_to is null
            order by t.external_id
            """
        ),
        {"user_id": TEAM_DEMO_USER_ID},
    ).mappings().all()
    return [str(row["id"]) for row in rows]


def _claim_tree(session: Session, slot: int) -> str:
    owned = _owned_tree_ids(session)
    if len(owned) >= slot:
        return owned[slot - 1]

    row = session.execute(
        text(
            """
            select t.id
            from trees t
            join sensors s on s.tree_id = t.id and s.is_real = false
            left join tree_partnerships tp on tp.tree_id = t.id and tp.active_to is null
            where t.stadtteil in ('Innenstadt-Ost', 'Innenstadt-West')
              and coalesce(t.name, '') <> 'Berta'
              and tp.id is null
            order by t.external_id
            limit 1
            """
        ),
    ).mappings().first()
    if not row:
        row = session.execute(
            text(
                """
                select t.id
                from trees t
                join sensors s on s.tree_id = t.id and s.is_real = false
                left join tree_partnerships tp on tp.tree_id = t.id
                  and tp.user_id = :user_id and tp.active_to is null
                where t.stadtteil in ('Innenstadt-Ost', 'Innenstadt-West')
                  and coalesce(t.name, '') <> 'Berta'
                  and tp.id is null
                order by t.external_id
                offset :offset
                limit 1
                """
            ),
            {"user_id": TEAM_DEMO_USER_ID, "offset": slot + 400},
        ).mappings().one()

    tree_id = str(row["id"])
    session.execute(
        text("update trees set status = 'adopted' where id = :tree_id"),
        {"tree_id": tree_id},
    )
    return tree_id


def _ensure_owner(session: Session, tree_id: str, streak: int) -> None:
    session.execute(
        text(
            """
            delete from tree_partnerships
            where tree_id = :tree_id
              and role = 'owner'
              and user_id <> :user_id
              and active_to is null
            """
        ),
        {"tree_id": tree_id, "user_id": TEAM_DEMO_USER_ID},
    )
    session.execute(
        text(
            """
            insert into tree_partnerships (tree_id, user_id, role, streak)
            values (:tree_id, :user_id, 'owner', :streak)
            on conflict do nothing
            """
        ),
        {"tree_id": tree_id, "user_id": TEAM_DEMO_USER_ID, "streak": streak},
    )
    session.execute(
        text(
            """
            update tree_partnerships
            set role = 'owner', streak = :streak, active_to = null, streak_frozen = false
            where tree_id = :tree_id and user_id = :user_id
            """
        ),
        {"tree_id": tree_id, "user_id": TEAM_DEMO_USER_ID, "streak": streak},
    )


def _ensure_member(session: Session, tree_id: str, user_id, streak: int) -> None:
    session.execute(
        text(
            """
            insert into tree_partnerships (tree_id, user_id, role, streak)
            values (:tree_id, :user_id, 'member', :streak)
            on conflict do nothing
            """
        ),
        {"tree_id": tree_id, "user_id": user_id, "streak": streak},
    )
    session.execute(
        text(
            """
            update tree_partnerships
            set role = 'member', streak = :streak, active_to = null
            where tree_id = :tree_id and user_id = :user_id
            """
        ),
        {"tree_id": tree_id, "user_id": user_id, "streak": streak},
    )


def _partner_tree_target(partner_index: int) -> int:
    return 2 + (partner_index % 5)


def _active_partnership_count(session: Session, user_id) -> int:
    row = session.execute(
        text(
            """
            select count(*) as count
            from tree_partnerships
            where user_id = :user_id
              and (active_to is null or active_to >= current_date)
            """
        ),
        {"user_id": user_id},
    ).mappings().one()
    return int(row["count"])


def _anchor_tree_for_partner(session: Session, partner_id) -> str | None:
    row = session.execute(
        text(
            """
            select tp.tree_id
            from tree_partnerships tp
            join tree_partnerships team on team.tree_id = tp.tree_id
            where tp.user_id = :partner_id
              and team.user_id = :team_id
              and team.role = 'owner'
              and tp.active_to is null
              and team.active_to is null
            order by tp.created_at
            limit 1
            """
        ),
        {"partner_id": partner_id, "team_id": TEAM_DEMO_USER_ID},
    ).mappings().first()
    return str(row["tree_id"]) if row else None


def _claim_nearby_tree(
    session: Session,
    partner_id,
    anchor_tree_id: str,
    pick_offset: int,
) -> str | None:
    row = session.execute(
        text(
            """
            select t.id
            from trees t
            join trees anchor on anchor.id = :anchor_id
            left join tree_partnerships owner_tp
              on owner_tp.tree_id = t.id
             and owner_tp.role = 'owner'
             and owner_tp.active_to is null
            left join tree_partnerships partner_tp
              on partner_tp.tree_id = t.id
             and partner_tp.user_id = :partner_id
             and (partner_tp.active_to is null or partner_tp.active_to >= current_date)
            where partner_tp.id is null
              and owner_tp.id is null
              and t.id <> :anchor_id
              and coalesce(t.name, '') <> 'Berta'
              and st_dwithin(t.geom::geography, anchor.geom::geography, :max_m)
              and st_distance(t.geom::geography, anchor.geom::geography) >= :min_m
            order by st_distance(t.geom::geography, anchor.geom::geography), t.external_id
            offset :pick_offset
            limit 1
            """
        ),
        {
            "anchor_id": anchor_tree_id,
            "partner_id": partner_id,
            "min_m": NEARBY_MIN_METERS,
            "max_m": NEARBY_MAX_METERS,
            "pick_offset": pick_offset,
        },
    ).mappings().first()
    return str(row["id"]) if row else None


def _ensure_partner_owner(session: Session, tree_id: str, partner_id, streak: int) -> None:
    session.execute(
        text(
            """
            insert into tree_partnerships (tree_id, user_id, role, streak)
            values (:tree_id, :user_id, 'owner', :streak)
            on conflict do nothing
            """
        ),
        {"tree_id": tree_id, "user_id": partner_id, "streak": streak},
    )
    session.execute(
        text(
            """
            update tree_partnerships
            set role = 'owner', streak = :streak, active_to = null, streak_frozen = false
            where tree_id = :tree_id and user_id = :user_id
            """
        ),
        {"tree_id": tree_id, "user_id": partner_id, "streak": streak},
    )
    session.execute(
        text("update trees set status = 'adopted' where id = :tree_id"),
        {"tree_id": tree_id},
    )


def _partner_owned_tree_ids(session: Session, partner_id) -> list[str]:
    rows = session.execute(
        text(
            """
            select tree_id
            from tree_partnerships
            where user_id = :user_id
              and role = 'owner'
              and active_to is null
            order by created_at, tree_id
            """
        ),
        {"user_id": partner_id},
    ).mappings().all()
    return [str(row["tree_id"]) for row in rows]


def _expand_partner_fleets(session: Session) -> int:
    created = 0
    for index, partner_id in enumerate(CO_PARTNER_IDS):
        target = _partner_tree_target(index)
        anchor_tree_id = _anchor_tree_for_partner(session, partner_id)
        if not anchor_tree_id:
            continue
        pick_offset = 0
        while _active_partnership_count(session, partner_id) < target:
            tree_id = _claim_nearby_tree(session, partner_id, anchor_tree_id, pick_offset)
            if not tree_id:
                break
            streak = 4 + (index % 7) + pick_offset
            _ensure_partner_owner(session, tree_id, partner_id, streak)
            created += 1
            pick_offset += 1
    return created


def _expand_second_degree_network(session: Session) -> int:
    created = 0
    for index, second_user_id in enumerate(SECOND_DEGREE_IDS):
        partner_id = CO_PARTNER_IDS[index]
        partner_trees = _partner_owned_tree_ids(session, partner_id)
        if not partner_trees:
            continue
        shared_tree_id = partner_trees[index % len(partner_trees)]
        _ensure_member(session, shared_tree_id, second_user_id, 3 + (index % 5))

        if _active_partnership_count(session, second_user_id) >= 2:
            continue
        own_tree_id = _claim_nearby_tree(
            session=session,
            partner_id=second_user_id,
            anchor_tree_id=shared_tree_id,
            pick_offset=index,
        )
        if own_tree_id:
            _ensure_partner_owner(session, own_tree_id, second_user_id, 4 + (index % 4))
            created += 1
    return created


def _expand_third_degree_network(session: Session) -> int:
    created = 0
    for index, third_user_id in enumerate(THIRD_DEGREE_IDS):
        second_user_id = SECOND_DEGREE_IDS[index]
        second_user_trees = _partner_owned_tree_ids(session, second_user_id)
        if not second_user_trees:
            continue
        shared_tree_id = second_user_trees[0]
        _ensure_member(session, shared_tree_id, third_user_id, 2 + (index % 4))

        if _active_partnership_count(session, third_user_id) >= 2:
            continue
        own_tree_id = _claim_nearby_tree(
            session=session,
            partner_id=third_user_id,
            anchor_tree_id=shared_tree_id,
            pick_offset=index + 3,
        )
        if own_tree_id:
            _ensure_partner_owner(session, own_tree_id, third_user_id, 3 + (index % 4))
            created += 1
    return created


def _recompute_scores(session: Session) -> None:
    user_ids = [TEAM_DEMO_USER_ID, *CO_PARTNER_IDS, *SECOND_DEGREE_IDS, *THIRD_DEGREE_IDS]
    session.execute(
        text(
            """
            update profiles p
            set score = coalesce((
                select sum(tp.streak)
                from tree_partnerships tp
                where tp.user_id = p.id
                  and (tp.active_to is null or tp.active_to >= current_date)
            ), 0)
            where p.id = any(:user_ids)
            """
        ),
        {"user_ids": user_ids},
    )


def seed(session: Session) -> int:
    _ensure_users(session)
    for slot in range(1, TREE_COUNT + 1):
        tree_id = _claim_tree(session, slot)
        owner_streak = 8 + slot
        _ensure_owner(session, tree_id, owner_streak)
        member_a = CO_PARTNER_IDS[(slot - 1) * MEMBERS_PER_TREE]
        member_b = CO_PARTNER_IDS[(slot - 1) * MEMBERS_PER_TREE + 1]
        _ensure_member(session, tree_id, member_a, owner_streak - 1)
        _ensure_member(session, tree_id, member_b, owner_streak - 2)

    created = _expand_partner_fleets(session)
    created += _expand_second_degree_network(session)
    created += _expand_third_degree_network(session)
    _recompute_scores(session)
    session.commit()
    return TREE_COUNT + created
