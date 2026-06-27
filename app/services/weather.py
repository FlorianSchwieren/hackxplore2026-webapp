from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy import text
from sqlmodel import Session

from app.config import get_settings


def _daily_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    daily = payload.get("daily") or {}
    dates = daily.get("time") or []
    temp_max = daily.get("temperature_2m_max") or []
    precip = daily.get("precipitation_sum") or []
    return [
        {
            "date": dates[index],
            "temp_max": temp_max[index] if index < len(temp_max) else None,
            "precip_mm": precip[index] if index < len(precip) else None,
        }
        for index in range(len(dates))
    ]


def fetch_forecast(session: Session) -> dict[str, Any]:
    settings = get_settings()
    params = {
        "latitude": settings.karlsruhe_lat,
        "longitude": settings.karlsruhe_lon,
        "current": "temperature_2m,relative_humidity_2m,precipitation",
        "daily": "temperature_2m_max,precipitation_sum",
        "timezone": "Europe/Berlin",
    }
    with httpx.Client(timeout=10) as client:
        response = client.get(f"{settings.open_meteo_base_url}/forecast", params=params)
        response.raise_for_status()
        payload = response.json()

    current = payload.get("current") or {}
    daily = _daily_rows(payload)
    session.execute(
        text(
            """
            insert into weather_snapshots (lat, lon, temp_c, precip_mm, humidity_pct, forecast_json)
            values (:lat, :lon, :temp_c, :precip_mm, :humidity_pct, cast(:forecast_json as jsonb))
            """
        ),
        {
            "lat": Decimal(str(settings.karlsruhe_lat)),
            "lon": Decimal(str(settings.karlsruhe_lon)),
            "temp_c": current.get("temperature_2m"),
            "precip_mm": current.get("precipitation"),
            "humidity_pct": current.get("relative_humidity_2m"),
            "forecast_json": response.text,
        },
    )
    session.commit()
    return {"current": current, "daily": daily}
