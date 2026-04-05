from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from .common.config import settings
from .common.logging import get_logger
from .extract.cities import read_cities
from .extract.geocoding import geocode_city
from .extract.openweather_air_pollution import fetch_air_pollution_history
from .load.storage import PublishResult, publish_outputs
from .transform.openweather_air_pollution_transform import build_gold_from_raw


log = get_logger(__name__)


@dataclass(frozen=True)
class PipelineRunResult:
    run_id: str
    source: str
    history_hours: int
    raw_files: list[Path]
    gold_path: Path | None
    postgres_table: str | None
    rows: int


def ensure_output_directories() -> tuple[Path, Path]:
    raw_dir = Path(settings.raw_dir)
    gold_dir = Path(settings.gold_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    gold_dir.mkdir(parents=True, exist_ok=True)
    return raw_dir, gold_dir


def build_runtime_window(history_hours: int) -> tuple[datetime, datetime]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=history_hours)
    return start, end


def run_extract_stage(raw_dir: Path, start: datetime, end: datetime, run_id: str) -> list[Path]:
    cities = read_cities(Path(settings.cities_file))
    raw_files: list[Path] = []

    for city in cities:
        coords = geocode_city(
            raw_dir=raw_dir,
            city=city.city,
            country_code=city.country_code,
            state=city.state,
        )
        raw_path = fetch_air_pollution_history(
            raw_dir=raw_dir,
            city=city.city,
            country_code=city.country_code,
            lat=coords.lat,
            lon=coords.lon,
            start=start,
            end=end,
            run_id=run_id,
        )
        raw_files.append(raw_path)

    return raw_files


def run_transform_stage(raw_files: list[Path]) -> pd.DataFrame:
    return build_gold_from_raw(raw_files=raw_files)


def run_load_stage(
    gold_df: pd.DataFrame, gold_dir: Path, table_name: str = "air_pollution_gold"
) -> PublishResult:
    return publish_outputs(gold_df=gold_df, gold_dir=gold_dir, table_name=table_name)


def run_pipeline_job(source: str = "openweather", history_hours: int | None = None) -> PipelineRunResult:
    resolved_history_hours = int(settings.history_hours if history_hours is None else history_hours)
    raw_dir, gold_dir = ensure_output_directories()
    start, end = build_runtime_window(resolved_history_hours)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    log.info("Starting pipeline", extra={"source": source, "history_hours": resolved_history_hours})

    raw_files = run_extract_stage(raw_dir=raw_dir, start=start, end=end, run_id=run_id)
    gold_df = run_transform_stage(raw_files=raw_files)
    publish_result = run_load_stage(gold_df=gold_df, gold_dir=gold_dir)

    result = PipelineRunResult(
        run_id=run_id,
        source=source,
        history_hours=resolved_history_hours,
        raw_files=raw_files,
        gold_path=publish_result.gold_path,
        postgres_table=publish_result.table_name,
        rows=len(gold_df),
    )

    log.info(
        "Pipeline complete",
        extra={
            "gold_path": str(result.gold_path) if result.gold_path is not None else None,
            "postgres_table": result.postgres_table,
            "rows": result.rows,
        },
    )
    return result
