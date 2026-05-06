"""Load raw air pollution responses from PostgreSQL."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import sqlalchemy as sa

from ..common.config import settings
from ..common.logging import get_logger
from ..extract.openweather_air_pollution import (
    RawAirPollutionRecord,
    _build_postgres_engine,
    raw_air_pollution_responses_table,
    cities_table,
)

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine


log = get_logger(__name__)


def load_raw_responses_by_pipeline_run_id(
    pipeline_run_id: int, engine: Engine | None = None
) -> list[RawAirPollutionRecord]:
    """
    Load all raw air pollution responses for a given pipeline run from PostgreSQL.

    Args:
        pipeline_run_id: Foreign key to pipeline_runs table
        engine: Optional SQLAlchemy engine. If not provided, creates a new engine
                to connect to the configured PostgreSQL database.

    Returns:
        List of RawAirPollutionRecord ordered by city_id, then request time window

    Raises:
        ValueError: if pipeline_run_id doesn't exist in the database
    """
    if engine is None:
        engine = _build_postgres_engine()

    with engine.begin() as connection:
        # Join raw responses with cities to get city and country_code
        stmt = (
            sa.select(
                raw_air_pollution_responses_table,
                cities_table.c.city,
                cities_table.c.country_code,
            )
            .join(
                cities_table,
                raw_air_pollution_responses_table.c.city_id == cities_table.c.id,
            )
            .where(raw_air_pollution_responses_table.c.pipeline_run_id == pipeline_run_id)
            .order_by(
                raw_air_pollution_responses_table.c.city_id,
                raw_air_pollution_responses_table.c.request_start_utc,
                raw_air_pollution_responses_table.c.request_end_utc,
            )
        )

        rows = connection.execute(stmt).mappings().fetchall()

        if not rows:
            log.warning(
                "No raw responses found for pipeline_run_id",
                extra={"pipeline_run_id": pipeline_run_id},
            )
            return []

        records: list[RawAirPollutionRecord] = []

        for row in rows:
            # Deserialize JSON payload if it's a string
            payload_json = row["payload_json"]
            if isinstance(payload_json, str):
                try:
                    payload_json = json.loads(payload_json)
                except json.JSONDecodeError as e:
                    log.error(
                        "Failed to deserialize payload_json",
                        extra={
                            "raw_response_id": row["id"],
                            "pipeline_run_id": pipeline_run_id,
                            "error": str(e),
                        },
                    )
                    payload_json = {}

            # Ensure datetime fields have timezone info
            request_start_utc = row["request_start_utc"]
            if isinstance(request_start_utc, datetime):
                if request_start_utc.tzinfo is None:
                    request_start_utc = request_start_utc.replace(tzinfo=timezone.utc)
            else:
                request_start_utc = datetime.fromisoformat(str(request_start_utc))
                if request_start_utc.tzinfo is None:
                    request_start_utc = request_start_utc.replace(tzinfo=timezone.utc)

            request_end_utc = row["request_end_utc"]
            if isinstance(request_end_utc, datetime):
                if request_end_utc.tzinfo is None:
                    request_end_utc = request_end_utc.replace(tzinfo=timezone.utc)
            else:
                request_end_utc = datetime.fromisoformat(str(request_end_utc))
                if request_end_utc.tzinfo is None:
                    request_end_utc = request_end_utc.replace(tzinfo=timezone.utc)

            fetched_at = row["fetched_at"]
            if isinstance(fetched_at, datetime):
                if fetched_at.tzinfo is None:
                    fetched_at = fetched_at.replace(tzinfo=timezone.utc)
            else:
                fetched_at = datetime.fromisoformat(str(fetched_at))
                if fetched_at.tzinfo is None:
                    fetched_at = fetched_at.replace(tzinfo=timezone.utc)

            record = RawAirPollutionRecord(
                raw_response_id=int(row["id"]),
                pipeline_run_id=int(row["pipeline_run_id"]),
                city_id=int(row["city_id"]),
                city=row["city"],
                country_code=row["country_code"],
                lat=float(row["lat"]),
                lon=float(row["lon"]),
                geo_id=row["geo_id"],
                request_start_utc=request_start_utc,
                request_end_utc=request_end_utc,
                status_code=int(row["status_code"]),
                record_count=int(row["record_count"]),
                payload_json=payload_json,
                fetched_at=fetched_at,
            )
            records.append(record)

        log.info(
            "Loaded raw responses from PostgreSQL",
            extra={
                "pipeline_run_id": pipeline_run_id,
                "response_count": len(records),
            },
        )

        return records
