from __future__ import annotations

import argparse

from pipeline.common.config import settings
from pipeline.extract.cities import seed_cities_from_file
from pipeline.orchestration import run_pipeline_job


def main() -> None:
    parser = argparse.ArgumentParser(description="City Air Tracker ETL pipeline")
    parser.add_argument("--source", default="openweather", choices=["openweather"])
    parser.add_argument("--history-hours", type=int, default=int(settings.history_hours))
    parser.add_argument("--seed-cities", action="store_true")
    args = parser.parse_args()

    if args.seed_cities:
        seed_cities_from_file(settings.cities_file)
        return

    run_pipeline_job(source=args.source, history_hours=args.history_hours)


if __name__ == "__main__":
    main()
