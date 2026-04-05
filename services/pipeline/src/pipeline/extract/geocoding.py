from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, text

from ..common.config import settings
from .http import RateLimiter, get_with_retries


@dataclass(frozen=True)
class Coords:
    lat: float
    lon: float


_limiter = RateLimiter(settings.max_calls_per_minute)

# OpenWeather Geocoding (direct)
GEO_URL = "https://api.openweathermap.org/geo/1.0/direct"


def _build_postgres_engine():
    return create_engine(settings.postgres_sqlalchemy_url)


def _lookup_city_id(connection, city: str, country_code: str, state: str | None) -> int:
    row = connection.execute(
        text(
            """
            SELECT id
            FROM cities
            WHERE city = :city
              AND country_code = :country_code
              AND (
                (:state IS NULL AND state IS NULL)
                OR state = :state
              )
            ORDER BY id
            LIMIT 1
            """
        ),
        {
            "city": city,
            "country_code": country_code,
            "state": state,
        },
    ).fetchone()

    if row is None:
        raise ValueError(
            f"City must exist in the cities table before geocoding cache can be used: "
            f"{city},{country_code},{state or ''}"
        )

    return int(row[0])


def _read_cached_coords(connection, city_id: int) -> Coords | None:
    row = connection.execute(
        text(
            """
            SELECT lat, lon
            FROM geocoding_cache
            WHERE city_id = :city_id
            """
        ),
        {"city_id": city_id},
    ).fetchone()

    if row is None:
        return None

    return Coords(lat=float(row[0]), lon=float(row[1]))


def _upsert_geocoding_cache(
    connection,
    *,
    city_id: int,
    query_text: str,
    lat: float,
    lon: float,
    provider_name: str | None,
    provider_state: str | None,
    provider_country: str | None,
) -> None:
    connection.execute(
        text(
            """
            INSERT INTO geocoding_cache (
                city_id,
                query_text,
                lat,
                lon,
                provider_name,
                provider_state,
                provider_country,
                fetched_at
            )
            VALUES (
                :city_id,
                :query_text,
                :lat,
                :lon,
                :provider_name,
                :provider_state,
                :provider_country,
                :fetched_at
            )
            ON CONFLICT (city_id)
            DO UPDATE SET
                query_text = EXCLUDED.query_text,
                lat = EXCLUDED.lat,
                lon = EXCLUDED.lon,
                provider_name = EXCLUDED.provider_name,
                provider_state = EXCLUDED.provider_state,
                provider_country = EXCLUDED.provider_country,
                fetched_at = EXCLUDED.fetched_at
            """
        ),
        {
            "city_id": city_id,
            "query_text": query_text,
            "lat": lat,
            "lon": lon,
            "provider_name": provider_name,
            "provider_state": provider_state,
            "provider_country": provider_country,
            "fetched_at": datetime.now(timezone.utc),
        },
    )


def geocode_city(raw_dir: Path, city: str, country_code: str, state: str | None = None) -> Coords:
    engine = _build_postgres_engine()

    with engine.begin() as connection:
        city_id = _lookup_city_id(connection, city=city, country_code=country_code, state=state)
        cached = _read_cached_coords(connection, city_id)
        if cached is not None:
            return cached

    if not settings.openweather_api_key or settings.openweather_api_key == "CHANGEME":
        raise ValueError("OPENWEATHER_API_KEY must be set in .env")

    q = f"{city},{country_code}"
    if state:
        q = f"{city},{state},{country_code}"

    _limiter.wait()
    resp = get_with_retries(
        GEO_URL,
        params={"q": q, "limit": 5, "appid": settings.openweather_api_key},
    )
    arr = resp.json()
    if not arr:
        raise ValueError(f"No geocoding results for: {q}")

    best = arr[0]  # deterministic choice for POC
    payload = {
        "query": q,
        "lat": float(best["lat"]),
        "lon": float(best["lon"]),
        "name": best.get("name"),
        "state": best.get("state"),
        "country": best.get("country"),
    }

    with engine.begin() as connection:
        city_id = _lookup_city_id(connection, city=city, country_code=country_code, state=state)
        _upsert_geocoding_cache(
            connection,
            city_id=city_id,
            query_text=payload["query"],
            lat=payload["lat"],
            lon=payload["lon"],
            provider_name=payload["name"],
            provider_state=payload["state"],
            provider_country=payload["country"],
        )

    return Coords(lat=payload["lat"], lon=payload["lon"])
