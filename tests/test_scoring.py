from datetime import UTC, datetime

from app.services import scoring
from app.services.scoring import daily_streak_next, today_berlin


def test_worked_example_1000_to_909() -> None:
    cared_for = [daily_streak_next(100, True) for _ in range(9)]
    forgotten = daily_streak_next(100, False)
    assert sum(cared_for) + forgotten == 909


def test_frozen_streak_is_preserved() -> None:
    assert daily_streak_next(12, False, frozen=True) == 12
    assert daily_streak_next(12, True, frozen=True) == 12


def test_missing_sensor_data_is_neutral() -> None:
    assert daily_streak_next(12, None) == 12


def test_heavy_rain_does_not_penalize() -> None:
    assert daily_streak_next(12, False, heavy_rain=True) == 12


def test_today_berlin_uses_berlin_date_semantics(monkeypatch) -> None:
    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            instant = datetime(2026, 6, 27, 22, 30, tzinfo=UTC)
            return instant.astimezone(tz) if tz is not None else instant

    monkeypatch.setattr(scoring, "datetime", FrozenDateTime)

    assert today_berlin().isoformat() == "2026-06-28"
