from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert as pg_insert

from ..common.config import settings


@dataclass(frozen=True)
class PublishResult:
    table_name: str | None
    gold_path: Path | None
    rows: int


GOLD_UPSERT_REQUIRED_COLUMNS = {
    "pipeline_run_id",
    "raw_response_id",
    "city_id",
    "ts",
    "city",
    "country_code",
    "lat",
    "lon",
    "geo_id",
    "aqi_category",
}


def _build_postgres_engine():
    return create_engine(settings.postgres_sqlalchemy_url)


def _build_gold_table(table_name: str) -> sa.Table:
    metadata = sa.MetaData()
    return sa.Table(
        table_name,
        metadata,
        sa.Column("id", sa.BigInteger()),
        sa.Column("pipeline_run_id", sa.BigInteger()),
        sa.Column("raw_response_id", sa.BigInteger()),
        sa.Column("city_id", sa.BigInteger()),
        sa.Column("ts", sa.DateTime(timezone=True)),
        sa.Column("city", sa.Text()),
        sa.Column("country_code", sa.Text()),
        sa.Column("lat", sa.Numeric(9, 6)),
        sa.Column("lon", sa.Numeric(9, 6)),
        sa.Column("geo_id", sa.Text()),
        sa.Column("aqi", sa.Integer()),
        sa.Column("co", sa.Numeric(12, 4)),
        sa.Column("no", sa.Numeric(12, 4)),
        sa.Column("no2", sa.Numeric(12, 4)),
        sa.Column("o3", sa.Numeric(12, 4)),
        sa.Column("so2", sa.Numeric(12, 4)),
        sa.Column("nh3", sa.Numeric(12, 4)),
        sa.Column("pm2_5", sa.Numeric(12, 4)),
        sa.Column("pm10", sa.Numeric(12, 4)),
        sa.Column("pm2_5_24h_avg", sa.Numeric(12, 4)),
        sa.Column("aqi_category", sa.Text()),
        sa.Column("risk_score", sa.Numeric(12, 4)),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )


def _normalize_gold_value(value):
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if hasattr(value, "item") and not isinstance(value, (str, bytes, dict)):
        try:
            return value.item()
        except ValueError:
            return value
    return value


def _prepare_gold_rows(gold_df: pd.DataFrame) -> list[dict]:
    rows: list[dict] = []
    for raw_row in gold_df.to_dict(orient="records"):
        row = {key: _normalize_gold_value(value) for key, value in raw_row.items()}
        missing_columns = sorted(GOLD_UPSERT_REQUIRED_COLUMNS - row.keys())
        if missing_columns:
            missing_list = ", ".join(missing_columns)
            raise ValueError(f"Gold DataFrame is missing required PostgreSQL columns: {missing_list}")
        rows.append(row)
    return rows


def _build_gold_upsert_statement(table_name: str, rows: list[dict]):
    if not rows:
        raise ValueError("Cannot build a gold-table upsert statement with no rows")

    gold_table = _build_gold_table(table_name)
    insert_stmt = pg_insert(gold_table).values(rows)
    excluded = insert_stmt.excluded

    update_columns = {
        column: getattr(excluded, column)
        for column in rows[0].keys()
        if column not in {"id", "created_at", "updated_at"}
    }
    update_columns["updated_at"] = sa.func.now()

    return insert_stmt.on_conflict_do_update(
        index_elements=[gold_table.c.geo_id, gold_table.c.ts],
        set_=update_columns,
    )


def _upsert_gold_rows(engine, gold_df: pd.DataFrame, table_name: str) -> None:
    rows = _prepare_gold_rows(gold_df)
    if not rows:
        return

    statement = _build_gold_upsert_statement(table_name, rows)
    with engine.begin() as connection:
        connection.execute(statement)


def publish_outputs(gold_df: pd.DataFrame, gold_dir: Path, table_name: str) -> PublishResult:
    postgres_table: str | None = None
    gold_path: Path | None = None

    if settings.use_postgres:
        engine = _build_postgres_engine()
        _upsert_gold_rows(engine=engine, gold_df=gold_df, table_name=table_name)
        postgres_table = table_name

    if settings.write_gold_parquet:
        gold_path = gold_dir / f"{table_name}.parquet"
        gold_df.to_parquet(gold_path, index=False)

    if postgres_table is None and gold_path is None:
        raise ValueError("At least one load target must be enabled: USE_POSTGRES=1 or WRITE_GOLD_PARQUET=1")

    return PublishResult(table_name=postgres_table, gold_path=gold_path, rows=len(gold_df))
