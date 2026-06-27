from typing import Protocol


class WaterProfile(Protocol):
    optimal_min_pct: float
    optimal_max_pct: float
    dry_critical_pct: float
    wet_critical_pct: float


def raw_to_pct(raw: int, dry: int, wet: int) -> float:
    if dry == wet:
        raise ValueError("calibration_dry and calibration_wet must differ")
    pct = (dry - raw) / (dry - wet) * 100.0
    return max(0.0, min(100.0, round(pct, 2)))


def pct_to_raw(moisture_pct: float, dry: int, wet: int) -> int:
    moisture_pct = max(0.0, min(100.0, moisture_pct))
    return round(dry - (moisture_pct / 100.0) * (dry - wet))


def health_score(moisture_pct: float, profile: WaterProfile) -> int:
    optimal_min = float(profile.optimal_min_pct)
    optimal_max = float(profile.optimal_max_pct)
    dry_critical = float(profile.dry_critical_pct)
    wet_critical = float(profile.wet_critical_pct)
    centre = (optimal_min + optimal_max) / 2

    if optimal_min <= moisture_pct <= optimal_max:
        half = (optimal_max - optimal_min) / 2 or 1
        return round(100 - 20 * abs(moisture_pct - centre) / half)
    if moisture_pct < optimal_min:
        span = (optimal_min - dry_critical) or 1
        return max(0, round(80 * (moisture_pct - dry_critical) / span))
    span = (wet_critical - optimal_max) or 1
    return max(0, round(80 * (wet_critical - moisture_pct) / span))


def in_healthy_band(moisture_pct: float, profile: WaterProfile) -> bool:
    return float(profile.optimal_min_pct) <= moisture_pct <= float(profile.optimal_max_pct)


def health_state(
    moisture_pct: float,
    profile: WaterProfile,
    streak: int = 0,
    thriving_threshold: int = 7,
) -> str:
    if moisture_pct < float(profile.dry_critical_pct):
        return "critical"
    if moisture_pct < float(profile.optimal_min_pct):
        return "thirsty"
    if moisture_pct <= float(profile.optimal_max_pct):
        return "thriving" if streak >= thriving_threshold else "healthy"
    if moisture_pct > float(profile.wet_critical_pct):
        return "overwatered"
    # The public enum has no separate "wet warning" bucket; only beyond wet_critical is overwatered.
    return "healthy"


def is_outlier_raw(raw: int, dry: int, wet: int, margin: int) -> bool:
    low = min(dry, wet) - margin
    high = max(dry, wet) + margin
    return raw < low or raw > high
