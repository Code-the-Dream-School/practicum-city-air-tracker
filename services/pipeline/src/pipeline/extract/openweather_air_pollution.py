from __future__ import annotations
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy import create_engine

from ..common.config import settings
from .http import RateLimiter, get_with_retries


# OpenWeather Air Pollution API (historical)
AIR_URL = "https://api.openweathermap.org/data/2.5/air_pollution/history"

_limiter = RateLimiter(settings.max_calls_per_minute)


@dataclass(frozen=True)
class RawAirPollutionRecord:
    raw_response_id: int
    pipeline_run_id: int
    city_id: int
    city: str
    country_code: str
    lat: float
    lon: float
    geo_id: str
    request_start_utc: datetime
    request_end_utc: datetime
    status_code: int
    record_count: int
    payload_json: dict
    fetched_at: datetime


def _geo_id(city: str, country_code: str, lat: float, lon: float) -> str:
    return f"{city},{country_code}:{lat:.4f},{lon:.4f}".replace(' ', '_')


metadata = sa.MetaData()

cities_table = sa.Table(
    "cities",
    metadata,
    sa.Column("id", sa.BigInteger()),
    sa.Column("city", sa.Text()),
    sa.Column("country_code", sa.Text()),
    sa.Column("state", sa.Text()),
)

pipeline_runs_table = sa.Table(
    "pipeline_runs",
    metadata,
    sa.Column("id", sa.BigInteger()),
    sa.Column("run_id", sa.Text()),
    sa.Column("source", sa.Text()),
    sa.Column("history_hours", sa.Integer()),
    sa.Column("window_start_utc", sa.DateTime(timezone=True)),
    sa.Column("window_end_utc", sa.DateTime(timezone=True)),
    sa.Column("status", sa.Text()),
    sa.Column("started_at", sa.DateTime(timezone=True)),
)

raw_air_pollution_responses_table = sa.Table(
    "raw_air_pollution_responses",
    metadata,
    sa.Column("id", sa.BigInteger()),
    sa.Column("pipeline_run_id", sa.BigInteger()),
    sa.Column("city_id", sa.BigInteger()),
    sa.Column("geo_id", sa.Text()),
    sa.Column("lat", sa.Numeric(9, 6)),
    sa.Column("lon", sa.Numeric(9, 6)),
    sa.Column("request_url", sa.Text()),
    sa.Column("request_start_utc", sa.DateTime(timezone=True)),
    sa.Column("request_end_utc", sa.DateTime(timezone=True)),
    sa.Column("status_code", sa.Integer()),
    sa.Column("record_count", sa.Integer()),
    sa.Column("payload_json", sa.JSON()),
    sa.Column("fetched_at", sa.DateTime(timezone=True)),
)


def _build_postgres_engine():
    return create_engine(settings.postgres_sqlalchemy_url)


def _normalize_db_datetime(value) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
    raise ValueError(f"Unsupported datetime value: {value!r}")


def _lookup_city_id(connection, city: str, country_code: str) -> int:
    row = connection.execute(
        sa.select(cities_table.c.id).where(
            cities_table.c.city == city,
            cities_table.c.country_code == country_code,
        )
    ).fetchone()
    if row is None:
        raise ValueError(f"City must exist in the cities table before extraction: {city},{country_code}")
    return int(row[0])


def _ensure_pipeline_run(connection, run_id: str, start: datetime, end: datetime) -> int:
    row = connection.execute(
        sa.select(pipeline_runs_table.c.id).where(pipeline_runs_table.c.run_id == run_id)
    ).fetchone()
    if row is not None:
        return int(row[0])

    result = connection.execute(
        pipeline_runs_table.insert().values(
            run_id=run_id,
            source="openweather",
            history_hours=int((end - start).total_seconds() // 3600),
            window_start_utc=start,
            window_end_utc=end,
            status="running",
            started_at=datetime.now(timezone.utc),
        )
    )
    inserted_primary_key = result.inserted_primary_key
    inserted_id = inserted_primary_key[0] if inserted_primary_key else None
    if inserted_id is None:
        row = connection.execute(
            sa.select(pipeline_runs_table.c.id).where(pipeline_runs_table.c.run_id == run_id)
        ).fetchone()
        if row is None:
            raise ValueError(f"Unable to persist pipeline run metadata for run_id={run_id}")
        return int(row[0])
    return int(inserted_id)


def _build_record(
    *,
    row,
    city: str,
    country_code: str,
    payload_json: dict,
) -> RawAirPollutionRecord:
    return RawAirPollutionRecord(
        raw_response_id=int(row.id),
        pipeline_run_id=int(row.pipeline_run_id),
        city_id=int(row.city_id),
        city=city,
        country_code=country_code,
        lat=float(row.lat),
        lon=float(row.lon),
        geo_id=row.geo_id,
        request_start_utc=row.request_start_utc,
        request_end_utc=row.request_end_utc,
        status_code=int(row.status_code),
        record_count=int(row.record_count),
        payload_json=payload_json,
        fetched_at=row.fetched_at,
    )


def _find_existing_raw_response(connection, city_id: int, start: datetime, end: datetime):
    rows = connection.execute(
        sa.select(raw_air_pollution_responses_table).where(
            raw_air_pollution_responses_table.c.city_id == city_id,
        )
    ).mappings().fetchall()

    normalized_start = _normalize_db_datetime(start)
    normalized_end = _normalize_db_datetime(end)

    for row in rows:
        row_start = _normalize_db_datetime(row["request_start_utc"])
        row_end = _normalize_db_datetime(row["request_end_utc"])
        if row_start == normalized_start and row_end == normalized_end:
            return row

    return None


def fetch_air_pollution_history(
    raw_dir: Path,
    city: str,
    country_code: str,
    lat: float,
    lon: float,
    start: datetime,
    end: datetime,
    run_id: str,
) -> RawAirPollutionRecord:
    del raw_dir

    if not settings.openweather_api_key or settings.openweather_api_key == "CHANGEME":
        raise ValueError("OPENWEATHER_API_KEY must be set in .env")

    geo_id = _geo_id(city, country_code, lat, lon)
    engine = _build_postgres_engine()

    with engine.begin() as connection:
        city_id = _lookup_city_id(connection, city=city, country_code=country_code)
        pipeline_run_id = _ensure_pipeline_run(connection, run_id=run_id, start=start, end=end)
        existing = _find_existing_raw_response(connection, city_id=city_id, start=start, end=end)

        if existing is not None:
            payload_json = existing["payload_json"]
            if isinstance(payload_json, str):
                payload_json = json.loads(payload_json)
            return _build_record(
                row=existing,
                city=city,
                country_code=country_code,
                payload_json=payload_json,
            )

    _limiter.wait()
    start_ts = int(start.replace(tzinfo=timezone.utc).timestamp())
    end_ts = int(end.replace(tzinfo=timezone.utc).timestamp())
    resp = get_with_retries(
        AIR_URL,
        params={
            "lat": lat,
            "lon": lon,
            "start": start_ts,
            "end": end_ts,
            "appid": settings.openweather_api_key,
        },
    )
    data = resp.json()
    fetched_at = datetime.now(timezone.utc)

    with engine.begin() as connection:
        city_id = _lookup_city_id(connection, city=city, country_code=country_code)
        pipeline_run_id = _ensure_pipeline_run(connection, run_id=run_id, start=start, end=end)
        result = connection.execute(
            raw_air_pollution_responses_table.insert().values(
                pipeline_run_id=pipeline_run_id,
                city_id=city_id,
                geo_id=geo_id,
                lat=lat,
                lon=lon,
                request_url=AIR_URL,
                request_start_utc=start,
                request_end_utc=end,
                status_code=resp.status_code,
                record_count=len(data.get("list", [])),
                payload_json=data,
                fetched_at=fetched_at,
            )
        )
        inserted_primary_key = result.inserted_primary_key
        inserted_id = inserted_primary_key[0] if inserted_primary_key else None
        if inserted_id is None:
            row = _find_existing_raw_response(connection, city_id=city_id, start=start, end=end)
        else:
            row = connection.execute(
                sa.select(raw_air_pollution_responses_table).where(
                    raw_air_pollution_responses_table.c.id == inserted_id
                )
            ).mappings().fetchone()

        if row is None:
            raise ValueError("Unable to persist raw air-pollution response in PostgreSQL")

    return _build_record(
        row=row,
        city=city,
        country_code=country_code,
        payload_json=data,
    )
