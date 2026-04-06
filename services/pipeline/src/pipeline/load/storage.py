from __future__ import annotations

from io import BytesIO
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert as pg_insert

from ..common.config import settings


@dataclass(frozen=True)
class PublishResult:
    table_name: str | None = None
    gold_path: Path | None = None
    azure_blob_path: str | None = None
    rows: int = 0


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


def _import_azure_blob_clients():
    try:
        from azure.core.exceptions import ResourceExistsError
        from azure.storage.blob import BlobServiceClient
    except ImportError as exc:
        raise ImportError(
            "Azure Blob publishing requires azure-storage-blob. Install dependencies from requirements.txt."
        ) from exc

    return BlobServiceClient, ResourceExistsError


def _build_blob_service_client():
    connection_string = settings.azure_storage_connection_string.strip()
    if not connection_string:
        raise ValueError(
            "WRITE_GOLD_AZURE_BLOB=1 requires AZURE_STORAGE_CONNECTION_STRING to be set"
        )

    BlobServiceClient, _ = _import_azure_blob_clients()
    return BlobServiceClient.from_connection_string(connection_string)


def _resolve_azure_blob_path(table_name: str) -> str:
    blob_path = settings.azure_blob_path.strip()
    if not blob_path:
        blob_path = f"{table_name}.parquet"
    return blob_path.format(table_name=table_name)


def _upload_gold_to_azure_blob(gold_df: pd.DataFrame, table_name: str) -> str:
    container_name = settings.azure_blob_container.strip()
    if not container_name:
        raise ValueError("WRITE_GOLD_AZURE_BLOB=1 requires AZURE_BLOB_CONTAINER to be set")

    blob_path = _resolve_azure_blob_path(table_name)
    service_client = _build_blob_service_client()
    _, ResourceExistsError = _import_azure_blob_clients()

    container_client = service_client.get_container_client(container_name)
    try:
        container_client.create_container()
    except ResourceExistsError:
        pass

    parquet_bytes = BytesIO()
    gold_df.to_parquet(parquet_bytes, index=False)
    parquet_bytes.seek(0)

    blob_client = service_client.get_blob_client(container=container_name, blob=blob_path)
    blob_client.upload_blob(parquet_bytes.getvalue(), overwrite=True)
    return blob_path


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
    azure_blob_path: str | None = None

    if settings.use_postgres:
        engine = _build_postgres_engine()
        _upsert_gold_rows(engine=engine, gold_df=gold_df, table_name=table_name)
        postgres_table = table_name

    if settings.write_gold_parquet:
        gold_path = gold_dir / f"{table_name}.parquet"
        gold_df.to_parquet(gold_path, index=False)

    if settings.write_gold_azure_blob:
        azure_blob_path = _upload_gold_to_azure_blob(gold_df=gold_df, table_name=table_name)

    if postgres_table is None and gold_path is None and azure_blob_path is None:
        raise ValueError(
            "At least one load target must be enabled: USE_POSTGRES=1, WRITE_GOLD_PARQUET=1, or WRITE_GOLD_AZURE_BLOB=1"
        )

    return PublishResult(
        table_name=postgres_table,
        gold_path=gold_path,
        azure_blob_path=azure_blob_path,
        rows=len(gold_df),
    )
