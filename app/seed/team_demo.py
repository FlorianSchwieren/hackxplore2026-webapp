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
TREE_NAME_PREFIX = "TeamDemo-"

CO_PARTNER_IDS = [seed_uuid(f"user:team-copartner:{index}") for index in range(1, CO_PARTNER_COUNT + 1)]
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


def _ensure_users(session: Session) -> None:
    _upsert_profile(session, TEAM_DEMO_USER_ID, TEAM_DEMO_NAME, TEAM_DEMO_EMAIL, True)
    for index, partner_id in enumerate(CO_PARTNER_IDS):
        email = f"team-copartner-{index + 1:02d}@baumpate.demo"
        _upsert_profile(session, partner_id, CO_PARTNER_NAMES[index], email, False)


def _claim_tree(session: Session, slot: int) -> str:
    tree_name = f"{TREE_NAME_PREFIX}{slot}"
    existing = session.execute(
        text("select id from trees where name = :name"),
        {"name": tree_name},
    ).mappings().first()
    if existing:
        return str(existing["id"])

    row = session.execute(
        text(
            """
            select t.id
            from trees t
            join sensors s on s.tree_id = t.id and s.is_real = false
            left join tree_partnerships tp on tp.tree_id = t.id and tp.active_to is null
            where t.stadtteil in ('Innenstadt-Ost', 'Innenstadt-West')
              and coalesce(t.name, '') <> 'Berta'
              and coalesce(t.name, '') not like :prefix || '%'
              and tp.id is null
            order by t.external_id
            limit 1
            """
        ),
        {"prefix": TREE_NAME_PREFIX},
    ).mappings().first()
    if not row:
        row = session.execute(
            text(
                """
                select t.id
                from trees t
                join sensors s on s.tree_id = t.id and s.is_real = false
                where t.stadtteil in ('Innenstadt-Ost', 'Innenstadt-West')
                  and coalesce(t.name, '') <> 'Berta'
                  and coalesce(t.name, '') not like :prefix || '%'
                order by t.external_id
                offset :offset
                limit 1
                """
            ),
            {"prefix": TREE_NAME_PREFIX, "offset": slot + 400},
        ).mappings().one()

    tree_id = str(row["id"])
    session.execute(
        text(
            """
            update trees
            set name = :name, status = 'adopted'
            where id = :tree_id
            """
        ),
        {"name": tree_name, "tree_id": tree_id},
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


def _recompute_scores(session: Session) -> None:
    user_ids = [TEAM_DEMO_USER_ID, *CO_PARTNER_IDS]
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

    _recompute_scores(session)
    session.commit()
    return TREE_COUNT
