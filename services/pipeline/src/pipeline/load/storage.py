from __future__ import annotations
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine

from ..common.config import settings


def publish_outputs(gold_df: pd.DataFrame, gold_dir: Path, table_name: str) -> Path:
    gold_path = gold_dir / f"{table_name}.parquet"
    gold_df.to_parquet(gold_path, index=False)

    if settings.use_postgres:
        engine = create_engine(
            f"postgresql+psycopg://{settings.postgres_user}:{settings.postgres_password}"
            f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
        )
        gold_df.to_sql(table_name, engine, if_exists="replace", index=False)

    return gold_path
