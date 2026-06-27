"""Shared pytest fixtures for API integration tests."""

from collections.abc import Generator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import get_session
import app.main as main_module

def _has_database() -> bool:
    get_settings.cache_clear()
    return bool(get_settings().database_url)


HAS_DATABASE = _has_database()

KARLSRUHE_BBOX = "8.35,48.98,8.45,49.03"


@pytest.fixture
def client() -> TestClient:
    return TestClient(main_module.app)


@pytest.fixture
def clear_settings() -> Generator[None, None, None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def dev_auth(monkeypatch: pytest.MonkeyPatch, clear_settings: None) -> None:
    monkeypatch.setenv("DEV_AUTH_DISABLED", "true")
    get_settings.cache_clear()


@pytest.fixture
def auth_required(monkeypatch: pytest.MonkeyPatch, clear_settings: None) -> None:
    monkeypatch.setenv("DEV_AUTH_DISABLED", "false")
    get_settings.cache_clear()


@pytest.fixture
def no_db(monkeypatch: pytest.MonkeyPatch, clear_settings: None) -> None:
    """Force no database_url even when .env defines one."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "")
    get_settings.cache_clear()


def _mock_session() -> MagicMock:
    session = MagicMock()
    result = MagicMock()
    result.mappings.return_value.all.return_value = []
    result.mappings.return_value.first.return_value = None
    result.mappings.return_value.one.return_value = {}
    result.scalar_one.return_value = 0
    session.execute.return_value = result
    return session


@pytest.fixture
def mock_db_session(no_db: None) -> Generator[MagicMock, None, None]:
    """Override get_session so routes can run without a real database."""
    session = _mock_session()

    def override_get_session() -> Generator[MagicMock, None, None]:
        yield session

    for target in (main_module.app, main_module.api):
        target.dependency_overrides[get_session] = override_get_session
    try:
        yield session
    finally:
        for target in (main_module.app, main_module.api):
            target.dependency_overrides.pop(get_session, None)
