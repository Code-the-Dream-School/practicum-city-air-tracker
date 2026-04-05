from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine

from ..common.config import settings


@dataclass(frozen=True)
class PublishResult:
    table_name: str | None
    gold_path: Path | None
    rows: int


def _build_postgres_engine():
    return create_engine(
        f"postgresql+psycopg://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )


def publish_outputs(gold_df: pd.DataFrame, gold_dir: Path, table_name: str) -> PublishResult:
    postgres_table: str | None = None
    gold_path: Path | None = None

    if settings.use_postgres:
        engine = _build_postgres_engine()
        gold_df.to_sql(table_name, engine, if_exists="replace", index=False)
        postgres_table = table_name

    if settings.write_gold_parquet:
        gold_path = gold_dir / f"{table_name}.parquet"
        gold_df.to_parquet(gold_path, index=False)

    if postgres_table is None and gold_path is None:
        raise ValueError("At least one load target must be enabled: USE_POSTGRES=1 or WRITE_GOLD_PARQUET=1")

    return PublishResult(table_name=postgres_table, gold_path=gold_path, rows=len(gold_df))
