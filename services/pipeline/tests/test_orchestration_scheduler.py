from __future__ import annotations

import pipeline.orchestration as orchestration
from pipeline.orchestration.scheduler import run_pipeline_job as scheduler_run_pipeline_job


def test_scheduler_run_pipeline_job_is_importable_and_delegates(monkeypatch):
    monkeypatch.setattr(orchestration, "run_pipeline_job", lambda source, history_hours: {"source": source, "history_hours": history_hours})

    result = scheduler_run_pipeline_job(source="openweather", history_hours=24)

    assert result == {"source": "openweather", "history_hours": 24}
