from __future__ import annotations

import pipeline.orchestration as orchestration


def run_pipeline_job(source: str = "openweather", history_hours: int | None = None):
    """Temporary compatibility shim around the shared pipeline runner.

    Prefect is the active orchestration direction for this repository. This
    wrapper remains in place temporarily so any code that still imports the old
    scheduler-facing module keeps delegating to the same shared runner.
    """
    return orchestration.run_pipeline_job(source=source, history_hours=history_hours)
