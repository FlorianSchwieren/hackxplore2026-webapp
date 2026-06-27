import random

from sqlalchemy import text
from sqlmodel import Session

from app.seed.common import seed_uuid

RANDOM_SEED = 42
DEMO_USER_1_ID = seed_uuid("user:alex@baumpate.demo")
DEMO_USER_2_ID = seed_uuid("user:sam@baumpate.demo")
TEAM_DEMO_USER_ID = seed_uuid("user:team@baumpate.demo")
TEAM_DEMO_EMAIL = "team@baumpate.demo"
TEAM_DEMO_NAME = "Taylor Team"


FIRST_NAMES = [
    "Mia",
    "Noah",
    "Emma",
    "Ben",
    "Lea",
    "Elias",
    "Lina",
    "Jonas",
    "Nina",
    "Theo",
]


def _ensure_auth_user(session: Session, user_id, email: str) -> None:
    session.execute(
        text(
            """
            insert into auth.users (
                id, aud, role, email, email_confirmed_at, created_at, updated_at,
                raw_app_meta_data, raw_user_meta_data, is_sso_user, is_anonymous
            )
            values (
                :id, 'authenticated', 'authenticated', :email, now(), now(), now(),
                '{"provider":"email","providers":["email"]}'::jsonb, '{}'::jsonb, false, false
            )
            on conflict (id) do update set email = excluded.email, updated_at = now()
            """
        ),
        {"id": user_id, "email": email},
    )


def _upsert_profile(session: Session, user_id, display_name: str, email: str, notify: bool) -> None:
    _ensure_auth_user(session, user_id, email)
    session.execute(
        text(
            """
            insert into profiles (id, display_name, email, notify_help_opt_in)
            values (:id, :display_name, :email, :notify)
            on conflict (id) do update set
                display_name = excluded.display_name,
                email = excluded.email,
                notify_help_opt_in = excluded.notify_help_opt_in
            """
        ),
        {"id": user_id, "display_name": display_name, "email": email, "notify": notify},
    )


def seed(session: Session, fake_count: int = 300) -> int:
    random.seed(RANDOM_SEED)
    _upsert_profile(session, DEMO_USER_1_ID, "Alex", "alex@baumpate.demo", True)
    _upsert_profile(session, DEMO_USER_2_ID, "Sam", "sam@baumpate.demo", True)
    for index in range(1, fake_count + 1):
        name = f"{random.choice(FIRST_NAMES)} {index}"
        _upsert_profile(
            session,
            seed_uuid(f"user:fake:{index}"),
            name,
            f"user{index:03d}@baumpate.demo",
            random.random() < 0.35,
        )
    session.commit()
    return fake_count + 2
