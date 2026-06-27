import sys
from collections.abc import Generator
from pathlib import Path

import psycopg
from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine

from app.config import get_settings


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.removeprefix("postgres://")
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


def _psycopg_database_url(url: str) -> str:
    if url.startswith("postgresql+psycopg://"):
        return "postgresql://" + url.removeprefix("postgresql+psycopg://")
    return url


def get_engine() -> Engine:
    database_url = get_settings().database_url
    if not database_url:
        raise RuntimeError("DATABASE_URL is required for database access")
    return create_engine(_normalize_database_url(database_url), pool_pre_ping=True)


engine = None


def session_context() -> Session:
    global engine
    if engine is None:
        engine = get_engine()
    return Session(engine)


def get_session() -> Generator[Session, None, None]:
    with session_context() as session:
        yield session


def apply_sql_file(path: str) -> None:
    sql_path = Path(path)
    if not sql_path.exists():
        raise FileNotFoundError(path)
    database_url = get_settings().database_url
    if not database_url:
        raise RuntimeError("DATABASE_URL is required for migrations")
    with psycopg.connect(_psycopg_database_url(database_url), autocommit=True) as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql_path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if len(argv) == 2 and argv[0] == "apply-sql":
        apply_sql_file(argv[1])
        return 0
    print("Usage: python -m app.db apply-sql <path>", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
