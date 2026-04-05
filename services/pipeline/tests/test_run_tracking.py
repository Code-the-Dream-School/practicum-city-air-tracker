from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

import pipeline.run_tracking as run_tracking


def _build_sqlite_engine(db_path: Path):
    engine = create_engine(f"sqlite+pysqlite:///{db_path}")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE pipeline_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL UNIQUE,
                    source TEXT NOT NULL,
                    history_hours INTEGER NOT NULL,
                    window_start_utc TEXT NOT NULL,
                    window_end_utc TEXT NOT NULL,
                    status TEXT NOT NULL,
                    city_count INTEGER NULL,
                    raw_response_count INTEGER NULL,
                    gold_row_count INTEGER NULL,
                    error_message TEXT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT NULL
                )
                """
            )
        )
    return engine


def test_create_pipeline_run_persists_running_row(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    engine = _build_sqlite_engine(tmp_path / "run-tracking.db")
    monkeypatch.setattr(run_tracking, "_build_postgres_engine", lambda: engine)

    run_id = "20260405T000000Z"
    pipeline_run_id = run_tracking.create_pipeline_run(
        run_id=run_id,
        source="openweather",
        history_hours=72,
        window_start_utc=datetime(2026, 4, 5, tzinfo=timezone.utc),
        window_end_utc=datetime(2026, 4, 8, tzinfo=timezone.utc),
    )

    assert pipeline_run_id == 1

    with engine.begin() as connection:
        row = connection.execute(
            text("SELECT run_id, status, source, history_hours FROM pipeline_runs WHERE id = 1")
        ).fetchone()

    assert row == (run_id, "running", "openweather", 72)


def test_update_pipeline_run_status_persists_completion_details(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    engine = _build_sqlite_engine(tmp_path / "run-tracking-update.db")
    monkeypatch.setattr(run_tracking, "_build_postgres_engine", lambda: engine)

    run_id = "20260405T000000Z"
    run_tracking.create_pipeline_run(
        run_id=run_id,
        source="openweather",
        history_hours=72,
        window_start_utc=datetime(2026, 4, 5, tzinfo=timezone.utc),
        window_end_utc=datetime(2026, 4, 8, tzinfo=timezone.utc),
    )

    run_tracking.update_pipeline_run_status(
        run_id,
        run_tracking.PipelineRunStatusUpdate(
            status="failed",
            city_count=4,
            raw_response_count=2,
            error_message="boom",
            finished_at=datetime(2026, 4, 5, 1, tzinfo=timezone.utc),
        ),
    )

    with engine.begin() as connection:
        row = connection.execute(
            text(
                """
                SELECT status, city_count, raw_response_count, error_message, finished_at
                FROM pipeline_runs
                WHERE run_id = :run_id
                """
            ),
            {"run_id": run_id},
        ).fetchone()

    assert row[0] == "failed"
    assert row[1] == 4
    assert row[2] == 2
    assert row[3] == "boom"
    assert row[4] is not None
