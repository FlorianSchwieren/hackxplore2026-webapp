import random

from sqlalchemy import text
from sqlmodel import Session

RANDOM_SEED = 42


def seed(session: Session, owner_count: int = 540) -> int:
    random.seed(RANDOM_SEED)
    users = session.execute(
        text("select id from profiles where email like 'user%@baumpate.demo' order by email")
    ).mappings().all()
    trees = session.execute(
        text(
            """
            select t.id, t.health_state
            from trees t
            join sensors s on s.tree_id = t.id
            where s.is_real = false
            order by t.external_id
            """
        )
    ).mappings().all()
    if not users or not trees:
        return 0
    selected = trees[: min(owner_count, len(trees))]
    created = 0
    for index, tree in enumerate(selected):
        user = users[index % len(users)]["id"]
        streak = random.randint(4, 35) if tree["health_state"] in {"healthy", "thriving"} else random.randint(0, 3)
        session.execute(
            text(
                """
                insert into tree_partnerships (tree_id, user_id, role, streak)
                values (:tree_id, :user_id, 'owner', :streak)
                on conflict do nothing
                """
            ),
            {"tree_id": tree["id"], "user_id": user, "streak": streak},
        )
        session.execute(
            text("update trees set status = 'adopted' where id = :tree_id"),
            {"tree_id": tree["id"]},
        )
        created += 1
        if index % 12 == 0 and len(users) > 1:
            member = users[(index + 7) % len(users)]["id"]
            session.execute(
                text(
                    """
                    insert into tree_partnerships (tree_id, user_id, role, streak)
                    values (:tree_id, :user_id, 'member', :streak)
                    on conflict do nothing
                    """
                ),
                {"tree_id": tree["id"], "user_id": member, "streak": max(streak - 2, 0)},
            )
            created += 1

    absence_rows = session.execute(
        text(
            """
            select id, tree_id, user_id
            from tree_partnerships
            where role = 'owner'
            order by created_at desc
            limit 8
            """
        )
    ).mappings().all()
    for row in absence_rows:
        session.execute(
            text(
                """
                insert into absences (user_id, tree_id, partnership_id, from_date, to_date, status)
                select :user_id, :tree_id, :partnership_id, current_date, current_date + 14, 'open'
                where not exists (
                    select 1 from absences
                    where partnership_id = :partnership_id
                      and status in ('open', 'covered')
                      and to_date >= current_date
                )
                """
            ),
            {"user_id": row["user_id"], "tree_id": row["tree_id"], "partnership_id": row["id"]},
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
            """
        )
    )
    session.commit()
    return created
