from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy import create_engine

from .common.config import settings


@dataclass(frozen=True)
class PipelineRunStatusUpdate:
    status: str
    city_count: int | None = None
    raw_response_count: int | None = None
    gold_row_count: int | None = None
    error_message: str | None = None
    finished_at: datetime | None = None


metadata = sa.MetaData()

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
    sa.Column("city_count", sa.Integer()),
    sa.Column("raw_response_count", sa.Integer()),
    sa.Column("gold_row_count", sa.Integer()),
    sa.Column("error_message", sa.Text()),
    sa.Column("started_at", sa.DateTime(timezone=True)),
    sa.Column("finished_at", sa.DateTime(timezone=True)),
)


def _build_postgres_engine():
    return create_engine(settings.postgres_sqlalchemy_url)


def create_pipeline_run(
    *,
    run_id: str,
    source: str,
    history_hours: int,
    window_start_utc: datetime,
    window_end_utc: datetime,
) -> int:
    engine = _build_postgres_engine()
    with engine.begin() as connection:
        existing = connection.execute(
            sa.select(pipeline_runs_table.c.id).where(pipeline_runs_table.c.run_id == run_id)
        ).fetchone()
        if existing is not None:
            return int(existing[0])

        result = connection.execute(
            pipeline_runs_table.insert().values(
                run_id=run_id,
                source=source,
                history_hours=history_hours,
                window_start_utc=window_start_utc,
                window_end_utc=window_end_utc,
                status="running",
                started_at=datetime.now(timezone.utc),
            )
        )

        inserted_primary_key = result.inserted_primary_key
        inserted_id = inserted_primary_key[0] if inserted_primary_key else None
        if inserted_id is None:
            existing = connection.execute(
                sa.select(pipeline_runs_table.c.id).where(pipeline_runs_table.c.run_id == run_id)
            ).fetchone()
            if existing is None:
                raise ValueError(f"Unable to create pipeline run row for run_id={run_id}")
            return int(existing[0])

        return int(inserted_id)


def update_pipeline_run_status(run_id: str, update: PipelineRunStatusUpdate) -> None:
    engine = _build_postgres_engine()
    values: dict[str, object] = {"status": update.status}

    if update.city_count is not None:
        values["city_count"] = update.city_count
    if update.raw_response_count is not None:
        values["raw_response_count"] = update.raw_response_count
    if update.gold_row_count is not None:
        values["gold_row_count"] = update.gold_row_count
    if update.error_message is not None:
        values["error_message"] = update.error_message
    if update.finished_at is not None:
        values["finished_at"] = update.finished_at

    with engine.begin() as connection:
        connection.execute(
            pipeline_runs_table.update()
            .where(pipeline_runs_table.c.run_id == run_id)
            .values(**values)
        )
