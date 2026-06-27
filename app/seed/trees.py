import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import text
from sqlmodel import Session

ROOT = Path(__file__).resolve().parents[2]
LOCAL_TREE_FILE = ROOT / "data" / "raw" / "karlsruhe_trees_citycenter.geojson"
GEOPORTAL_URL = (
    "https://geoportal.karlsruhe.de/ags04/rest/services/Hosted/Baumkataster/"
    "FeatureServer/2/query"
)


def local_features() -> Iterable[dict[str, Any]]:
    payload = json.loads(LOCAL_TREE_FILE.read_text(encoding="utf-8"))
    yield from payload["features"]


def citywide_features(page_size: int = 2000) -> Iterable[dict[str, Any]]:
    offset = 0
    with httpx.Client(timeout=30) as client:
        while True:
            response = client.get(
                GEOPORTAL_URL,
                params={
                    "where": "stadtteil IS NOT NULL",
                    "outFields": "objectid,lfdbnr,artdeut,artlat,baumart_allgemein,baumgruppe,stadtteil",
                    "returnGeometry": "true",
                    "outSR": 4326,
                    "resultOffset": offset,
                    "resultRecordCount": page_size,
                    "f": "geojson",
                },
            )
            response.raise_for_status()
            features = response.json().get("features") or []
            if not features:
                break
            yield from features
            offset += len(features)


def _resolve_profile_id(session: Session, artlat: str | None, category: str) -> str:
    if artlat:
        row = session.execute(
            text(
                """
                select id
                from species_water_profiles
                where
                  (match_kind = 'species_lat' and :artlat ilike match_value || '%')
                  or (match_kind = 'category' and match_value = :category)
                  or (match_kind = 'category' and match_value = 'default')
                order by
                  case
                    when match_kind = 'species_lat' and :artlat ilike match_value || '%' then 2
                    when match_kind = 'category' and match_value = :category then 1
                    else 0
                  end desc,
                  priority desc
                limit 1
                """
            ),
            {"artlat": artlat, "category": category},
        ).mappings().one()
    else:
        row = session.execute(
            text(
                """
                select id
                from species_water_profiles
                where
                  (match_kind = 'category' and match_value = :category)
                  or (match_kind = 'category' and match_value = 'default')
                order by
                  case when match_value = :category then 1 else 0 end desc,
                  priority desc
                limit 1
                """
            ),
            {"category": category},
        ).mappings().one()
    return str(row["id"])


def seed(session: Session, citywide: bool = False, limit: int | None = None) -> int:
    count = 0
    features = citywide_features() if citywide else local_features()
    for feature in features:
        props = feature["properties"]
        lon, lat = feature["geometry"]["coordinates"][:2]
        category = props.get("baumart_allgemein") or "unbekannt"
        profile_id = _resolve_profile_id(session, props.get("artlat"), category)
        session.execute(
            text(
                """
                insert into trees (
                    external_id, lfdbnr, artdeut, artlat, baumart_allgemein, baumgruppe,
                    stadtteil, geom, species_profile_id
                )
                values (
                    :external_id, :lfdbnr, :artdeut, :artlat, :baumart_allgemein, :baumgruppe,
                    :stadtteil, st_setsrid(st_makepoint(:lon, :lat), 4326), :species_profile_id
                )
                on conflict (external_id) do update set
                    lfdbnr = excluded.lfdbnr,
                    artdeut = excluded.artdeut,
                    artlat = excluded.artlat,
                    baumart_allgemein = excluded.baumart_allgemein,
                    baumgruppe = excluded.baumgruppe,
                    stadtteil = excluded.stadtteil,
                    geom = excluded.geom,
                    species_profile_id = excluded.species_profile_id
                """
            ),
            {
                "external_id": props["objectid"],
                "lfdbnr": props.get("lfdbnr"),
                "artdeut": props.get("artdeut"),
                "artlat": props.get("artlat"),
                "baumart_allgemein": category,
                "baumgruppe": props.get("baumgruppe"),
                "stadtteil": props["stadtteil"],
                "lon": lon,
                "lat": lat,
                "species_profile_id": profile_id,
            },
        )
        count += 1
        if count % 1000 == 0:
            session.commit()
        if limit and count >= limit:
            break
    session.commit()
    return count
