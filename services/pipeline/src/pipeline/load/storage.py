from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from abc import ABC, abstractmethod
import pandas as pd
from sqlalchemy import create_engine

from ..common.config import settings


@dataclass
class PublishResult:
    parquet_path: Path | None = None
    postgres_table: str | None = None


class GoldStorageStrategy(ABC):
    @abstractmethod
    def publish(self, gold_df: pd.DataFrame, gold_dir: Path, table_name: str) -> PublishResult:
        raise NotImplementedError


class ParquetStorageStrategy(GoldStorageStrategy):
    def publish(self, gold_df: pd.DataFrame, gold_dir: Path, table_name: str) -> PublishResult:
        gold_path = gold_dir / f"{table_name}.parquet"
        gold_df.to_parquet(gold_path, index=False)
        return PublishResult(parquet_path=gold_path)


class PostgresStorageStrategy(GoldStorageStrategy):
    def publish(self, gold_df: pd.DataFrame, gold_dir: Path, table_name: str) -> PublishResult:
        _ = gold_dir  # Kept to preserve interface parity with all strategies.
        engine = create_engine(
            f"postgresql+psycopg://{settings.postgres_user}:{settings.postgres_password}"
            f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
        )
        gold_df.to_sql(table_name, engine, if_exists="replace", index=False)
        return PublishResult(postgres_table=table_name)


class CombinedStorageStrategy(GoldStorageStrategy):
    def __init__(self, parquet: GoldStorageStrategy, postgres: GoldStorageStrategy) -> None:
        self._parquet = parquet
        self._postgres = postgres

    def publish(self, gold_df: pd.DataFrame, gold_dir: Path, table_name: str) -> PublishResult:
        parquet_result = self._parquet.publish(gold_df=gold_df, gold_dir=gold_dir, table_name=table_name)
        postgres_result = self._postgres.publish(gold_df=gold_df, gold_dir=gold_dir, table_name=table_name)
        return PublishResult(
            parquet_path=parquet_result.parquet_path,
            postgres_table=postgres_result.postgres_table,
        )


def build_storage_strategy(backend: str) -> GoldStorageStrategy:
    normalized = backend.strip().lower()
    if normalized == "parquet":
        return ParquetStorageStrategy()
    if normalized == "postgres":
        return PostgresStorageStrategy()
    if normalized == "both":
        return CombinedStorageStrategy(
            parquet=ParquetStorageStrategy(),
            postgres=PostgresStorageStrategy(),
        )
    raise ValueError(f"Unsupported GOLD_STORAGE_BACKEND: {backend}")


def publish_outputs(gold_df: pd.DataFrame, gold_dir: Path, table_name: str) -> PublishResult:
    strategy = build_storage_strategy(settings.gold_storage_backend)
    return strategy.publish(gold_df=gold_df, gold_dir=gold_dir, table_name=table_name)
