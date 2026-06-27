import pytest

from app.calibration import (
    health_score,
    health_state,
    in_healthy_band,
    is_outlier_raw,
    pct_to_raw,
    raw_to_pct,
)


class Profile:
    optimal_min_pct = 30
    optimal_max_pct = 60
    dry_critical_pct = 15
    wet_critical_pct = 80


def test_raw_to_pct_raises_when_dry_equals_wet() -> None:
    with pytest.raises(ValueError, match="calibration_dry and calibration_wet must differ"):
        raw_to_pct(1500, dry=1500, wet=1500)


def test_in_healthy_band_is_inclusive_at_boundaries() -> None:
    assert in_healthy_band(Profile.optimal_min_pct, Profile()) is True
    assert in_healthy_band(Profile.optimal_max_pct, Profile()) is True
    assert in_healthy_band(Profile.optimal_min_pct - 0.01, Profile()) is False
    assert in_healthy_band(Profile.optimal_max_pct + 0.01, Profile()) is False


def test_raw_to_pct_inverts_capacitive_reading() -> None:
    assert raw_to_pct(3099, dry=3099, wet=1500) == 0
    assert raw_to_pct(1500, dry=3099, wet=1500) == 100
    assert raw_to_pct(2299, dry=3099, wet=1500) == 50.03


def test_pct_to_raw_round_trips_nominal_values() -> None:
    raw = pct_to_raw(42, dry=3099, wet=1500)
    assert raw_to_pct(raw, dry=3099, wet=1500) == 42.03


def test_health_state_boundaries() -> None:
    assert health_state(10, Profile()) == "critical"
    assert health_state(20, Profile()) == "thirsty"
    assert health_state(45, Profile()) == "healthy"
    assert health_state(45, Profile(), streak=7) == "thriving"
    assert health_state(85, Profile()) == "overwatered"


def test_health_state_wet_warning_range_is_not_overwatered() -> None:
    assert health_state(Profile.optimal_max_pct + 1, Profile()) == "healthy"
    assert health_state(Profile.wet_critical_pct, Profile()) == "healthy"


def test_health_state_overwatered_only_above_wet_critical() -> None:
    assert health_state(Profile.wet_critical_pct - 1, Profile()) != "overwatered"
    assert health_state(Profile.wet_critical_pct, Profile()) != "overwatered"
    assert health_state(Profile.wet_critical_pct + 1, Profile()) == "overwatered"


def test_health_score_shape() -> None:
    assert health_score(45, Profile()) == 100
    assert health_score(30, Profile()) == 80
    assert health_score(15, Profile()) == 0
    assert health_score(80, Profile()) == 0


def test_outlier_raw_gate_uses_calibration_margin() -> None:
    assert is_outlier_raw(85, dry=3099, wet=1500, margin=250)
    assert is_outlier_raw(3400, dry=3099, wet=1500, margin=250)
    assert not is_outlier_raw(1900, dry=3099, wet=1500, margin=250)
