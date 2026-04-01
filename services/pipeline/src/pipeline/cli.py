from __future__ import annotations

import argparse

from pipeline.common.config import settings
from pipeline.orchestration import run_pipeline_job


def main() -> None:
    parser = argparse.ArgumentParser(description="City Air Tracker ETL pipeline")
    parser.add_argument("--source", default="openweather", choices=["openweather"])
    parser.add_argument("--history-hours", type=int, default=int(settings.history_hours))
    args = parser.parse_args()
    run_pipeline_job(source=args.source, history_hours=args.history_hours)


if __name__ == "__main__":
    main()
