from __future__ import annotations

import sys

import pytest

import pipeline.prefect_runtime as prefect_runtime


def test_run_pipeline_flow_delegates_to_shared_runner(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(prefect_runtime, "_ensure_prefect_available", lambda: None)
    monkeypatch.setattr(
        prefect_runtime,
        "run_pipeline_job",
        lambda source, history_hours: {"source": source, "history_hours": history_hours},
    )

    result = prefect_runtime.run_pipeline_flow(source="openweather", history_hours=24)

    assert result == {"source": "openweather", "history_hours": 24}


def test_main_parses_args_and_calls_prefect_flow(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, object] = {}

    monkeypatch.setattr(sys, "argv", ["pipeline.prefect_runtime", "--source", "openweather", "--history-hours", "48"])
    monkeypatch.setattr(
        prefect_runtime,
        "run_pipeline_flow",
        lambda source, history_hours: captured.update(source=source, history_hours=history_hours),
    )

    prefect_runtime.main()

    assert captured == {"source": "openweather", "history_hours": 48}


def test_run_pipeline_flow_raises_helpful_error_when_prefect_is_missing():
    if prefect_runtime.PREFECT_AVAILABLE:
        pytest.skip("Prefect is installed in this environment")

    with pytest.raises(RuntimeError, match="Prefect is not installed"):
        prefect_runtime.run_pipeline_flow()
