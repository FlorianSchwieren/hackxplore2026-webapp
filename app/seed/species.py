from decimal import Decimal

from sqlalchemy import text
from sqlmodel import Session

PROFILES = [
    ("category", "Laubbaum", 30, 60, 15, 80, "medium", 0),
    ("category", "Nadelbaum", 25, 55, 12, 78, "medium", 0),
    ("category", "Obstbaum", 35, 65, 18, 82, "low", 0),
    ("category", "Palme", 20, 50, 10, 75, "high", 0),
    ("category", "Topograph. Baum", 30, 60, 15, 80, "medium", 0),
    ("category", "unbekannt", 30, 60, 15, 80, "medium", 0),
    ("category", "default", 30, 60, 15, 80, "medium", 0),
    ("species_lat", "Carpinus betulus", 30, 60, 15, 80, "medium", 10),
    ("species_lat", "Acer platanoides", 28, 58, 14, 80, "medium", 10),
    ("species_lat", "Acer campestre", 22, 52, 12, 78, "high", 10),
    ("species_lat", "Platanus", 25, 55, 12, 80, "high", 10),
    ("species_lat", "Aesculus hippocastanum", 35, 65, 18, 82, "low", 10),
    ("species_lat", "Quercus rubra", 28, 58, 14, 80, "medium", 10),
    ("species_lat", "Quercus", 25, 55, 12, 80, "high", 10),
    ("species_lat", "Tilia cordata", 35, 65, 18, 82, "low", 10),
    ("species_lat", "Tilia", 33, 63, 17, 82, "low", 10),
    ("species_lat", "Betula pendula", 35, 68, 20, 84, "low", 10),
    ("species_lat", "Fraxinus excelsior", 30, 60, 15, 80, "medium", 10),
    ("species_lat", "Robinia pseudoacacia", 20, 50, 10, 78, "high", 10),
]


def seed(session: Session) -> int:
    for row in PROFILES:
        session.execute(
            text(
                """
                insert into species_water_profiles (
                    match_kind, match_value, optimal_min_pct, optimal_max_pct,
                    dry_critical_pct, wet_critical_pct, drought_tolerance, priority
                )
                values (
                    :match_kind, :match_value, :optimal_min_pct, :optimal_max_pct,
                    :dry_critical_pct, :wet_critical_pct, :drought_tolerance, :priority
                )
                on conflict (match_value) do update set
                    match_kind = excluded.match_kind,
                    optimal_min_pct = excluded.optimal_min_pct,
                    optimal_max_pct = excluded.optimal_max_pct,
                    dry_critical_pct = excluded.dry_critical_pct,
                    wet_critical_pct = excluded.wet_critical_pct,
                    drought_tolerance = excluded.drought_tolerance,
                    priority = excluded.priority
                """
            ),
            {
                "match_kind": row[0],
                "match_value": row[1],
                "optimal_min_pct": Decimal(row[2]),
                "optimal_max_pct": Decimal(row[3]),
                "dry_critical_pct": Decimal(row[4]),
                "wet_critical_pct": Decimal(row[5]),
                "drought_tolerance": row[6],
                "priority": row[7],
            },
        )
    session.commit()
    return len(PROFILES)
