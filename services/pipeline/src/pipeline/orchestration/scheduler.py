from __future__ import annotations

import pipeline.orchestration as orchestration


def run_pipeline_job(source: str = "openweather", history_hours: int | None = None):
    """Scheduler-compatible entrypoint for pipeline execution."""
    return orchestration.run_pipeline_job(source=source, history_hours=history_hours)
