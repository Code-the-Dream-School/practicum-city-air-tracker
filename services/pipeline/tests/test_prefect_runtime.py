from __future__ import annotations

import logging
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


def test_prefect_flow_does_not_add_duplicate_lifecycle_logs(
    monkeypatch: pytest.MonkeyPatch,
):
    """run_pipeline_flow must not add extra lifecycle logs on top of those
    emitted by the shared runner (run_pipeline_job). The wrapper itself
    should not emit its own start/complete messages that duplicate what the
    orchestration layer already records."""

    orchestration_messages: list[str] = []
    wrapper_messages: list[str] = []

    def fake_run_pipeline_job(source, history_hours):
        inner_log = logging.getLogger("pipeline.orchestration")
        inner_log.info("Pipeline starting")
        inner_log.info("Pipeline succeeded")
        return {"source": source, "history_hours": history_hours}

    monkeypatch.setattr(prefect_runtime, "_ensure_prefect_available", lambda: None)
    monkeypatch.setattr(prefect_runtime, "run_pipeline_job", fake_run_pipeline_job)

    class _Capture(logging.Handler):
        def __init__(self, store: list) -> None:
            super().__init__()
            self.store = store

        def emit(self, record: logging.LogRecord) -> None:
            self.store.append(record.getMessage())

    orch_handler = _Capture(orchestration_messages)
    wrapper_handler = _Capture(wrapper_messages)

    orch_logger = logging.getLogger("pipeline.orchestration")
    wrapper_logger = logging.getLogger("pipeline.prefect_runtime")
    orch_logger.addHandler(orch_handler)
    wrapper_logger.addHandler(wrapper_handler)
    try:
        prefect_runtime.run_pipeline_flow(source="openweather", history_hours=24)
    finally:
        orch_logger.removeHandler(orch_handler)
        wrapper_logger.removeHandler(wrapper_handler)

    # The shared runner messages must be present.
    assert any("Pipeline starting" in m for m in orchestration_messages)
    assert any("Pipeline succeeded" in m for m in orchestration_messages)

    # The Prefect wrapper must not emit its own duplicative lifecycle logs.
    duplicates = [
        m for m in wrapper_messages
        if any(kw in m for kw in ("Pipeline starting", "Pipeline complete", "Pipeline succeeded", "Pipeline failed"))
    ]
    assert duplicates == [], f"Prefect wrapper emitted duplicate lifecycle logs: {duplicates}"
