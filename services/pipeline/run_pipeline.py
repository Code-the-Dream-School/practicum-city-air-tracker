import argparse
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Any

from src.pipeline.common.config import settings
from src.pipeline.common.logging import get_logger
from src.pipeline.extract.cities import read_cities
from src.pipeline.extract.geocoding import geocode_city
from src.pipeline.extract.openweather_air_pollution import fetch_air_pollution_history
from src.pipeline.transform.openweather_air_pollution_transform import build_gold_from_raw
from src.pipeline.load.storage import publish_outputs


log = get_logger(__name__)


def _normalize_publish_result(publish_result: Any) -> tuple[Path | None, str | None]:
    """Support both structured and Path-only publish return values."""
    if isinstance(publish_result, Path):
        return publish_result, None

    parquet_path = getattr(publish_result, "parquet_path", None)
    postgres_table = getattr(publish_result, "postgres_table", None)
    return parquet_path, postgres_table


def main() -> None:
    parser = argparse.ArgumentParser(description="City Air Tracker ETL pipeline")
    parser.add_argument("--source", default="openweather", choices=["openweather"])
    parser.add_argument("--history-hours", type=int, default=int(settings.history_hours))
    args = parser.parse_args()

    raw_dir = Path(settings.raw_dir)
    gold_dir = Path(settings.gold_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    gold_dir.mkdir(parents=True, exist_ok=True)

    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=args.history_hours)

    log.info("Starting pipeline", extra={"source": args.source, "history_hours": args.history_hours})

    cities = read_cities(Path(settings.cities_file))
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    # Extract
    raw_files = []
    for c in cities:
        coords = geocode_city(
            raw_dir=raw_dir,
            city=c.city,
            country_code=c.country_code,
            state=c.state,
        )
        raw_path = fetch_air_pollution_history(
            raw_dir=raw_dir,
            city=c.city,
            country_code=c.country_code,
            lat=coords.lat,
            lon=coords.lon,
            start=start,
            end=end,
            run_id=run_id,
        )
        raw_files.append(raw_path)

    # Transform
    gold_df = build_gold_from_raw(raw_files=raw_files)

    # Load
    publish_result = publish_outputs(gold_df=gold_df, gold_dir=gold_dir, table_name="air_pollution_gold")
    parquet_path, postgres_table = _normalize_publish_result(publish_result)

    log.info(
        "Pipeline complete",
        extra={
            "gold_parquet_path": str(parquet_path) if parquet_path else None,
            "gold_postgres_table": postgres_table,
            "rows": len(gold_df),
        },
    )


if __name__ == "__main__":
    main()
