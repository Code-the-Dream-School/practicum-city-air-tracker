from datetime import datetime, timezone
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine, text

import pipeline.extract.openweather_air_pollution as air_module


def _build_sqlite_engine(db_path: Path):
    engine = create_engine(f"sqlite+pysqlite:///{db_path}")
    metadata = sa.MetaData()
    sa.Table(
        "cities",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("city", sa.Text(), nullable=False),
        sa.Column("country_code", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
    )
    sa.Table(
        "pipeline_runs",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.Text(), nullable=False, unique=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("history_hours", sa.Integer(), nullable=False),
        sa.Column("window_start_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
    )
    sa.Table(
        "raw_air_pollution_responses",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("pipeline_run_id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=False),
        sa.Column("geo_id", sa.Text(), nullable=False),
        sa.Column("lat", sa.Numeric(9, 6), nullable=False),
        sa.Column("lon", sa.Numeric(9, 6), nullable=False),
        sa.Column("request_url", sa.Text(), nullable=False),
        sa.Column("request_start_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_end_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("record_count", sa.Integer(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
    )
    metadata.create_all(engine)
    return engine


def test_fetch_air_pollution_history_persists_raw_response(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    engine = _build_sqlite_engine(tmp_path / "raw-extract.db")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO cities (city, country_code, state, is_active)
                VALUES ('Toronto', 'CA', 'ON', 1)
                """
            )
        )

    class DummyResponse:
        status_code = 200

        def json(self):
            return {
                "list": [
                    {
                        "dt": 1735689600,
                        "main": {"aqi": 2},
                        "components": {"pm2_5": 10.0, "pm10": 20.0},
                    }
                ]
            }

    monkeypatch.setattr(air_module, "_build_postgres_engine", lambda: engine)
    monkeypatch.setattr(air_module._limiter, "wait", lambda: None)
    monkeypatch.setattr(air_module, "get_with_retries", lambda *args, **kwargs: DummyResponse())
    monkeypatch.setattr(air_module.settings, "openweather_api_key", "test-key")

    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    end = datetime(2025, 1, 2, tzinfo=timezone.utc)
    record = air_module.fetch_air_pollution_history(
        raw_dir=tmp_path,
        city="Toronto",
        country_code="CA",
        lat=43.6535,
        lon=-79.3839,
        start=start,
        end=end,
        run_id="20250405T000000Z",
    )

    assert record.city == "Toronto"
    assert record.country_code == "CA"
    assert record.record_count == 1

    with engine.begin() as connection:
        run_count = connection.execute(text("SELECT COUNT(*) FROM pipeline_runs")).scalar_one()
        raw_count = connection.execute(text("SELECT COUNT(*) FROM raw_air_pollution_responses")).scalar_one()

    assert run_count == 1
    assert raw_count == 1


def test_fetch_air_pollution_history_reuses_existing_raw_response(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    engine = _build_sqlite_engine(tmp_path / "raw-extract-cache.db")
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    end = datetime(2025, 1, 2, tzinfo=timezone.utc)

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO cities (id, city, country_code, state, is_active)
                VALUES (1, 'Toronto', 'CA', 'ON', 1)
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO pipeline_runs (
                    id, run_id, source, history_hours, window_start_utc, window_end_utc, status, started_at
                )
                VALUES (
                    1, '20250405T000000Z', 'openweather', 24, :start, :end, 'running', :start
                )
                """
            ),
            {"start": start, "end": end},
        )
        connection.execute(
            text(
                """
                INSERT INTO raw_air_pollution_responses (
                    id, pipeline_run_id, city_id, geo_id, lat, lon, request_url,
                    request_start_utc, request_end_utc, status_code, record_count,
                    payload_json, fetched_at
                )
                VALUES (
                    1, 1, 1, 'Toronto,CA:43.6535,-79.3839', 43.6535, -79.3839,
                    'https://api.openweathermap.org/data/2.5/air_pollution/history',
                    :start, :end, 200, 1, :payload, :start
                )
                """
            ),
            {
                "start": start,
                "end": end,
                "payload": '{"list":[{"dt":1735689600,"main":{"aqi":2},"components":{"pm2_5":10.0,"pm10":20.0}}]}',
            },
        )

    called = {"value": False}
    monkeypatch.setattr(air_module, "_build_postgres_engine", lambda: engine)
    monkeypatch.setattr(air_module._limiter, "wait", lambda: None)
    monkeypatch.setattr(
        air_module,
        "get_with_retries",
        lambda *args, **kwargs: called.__setitem__("value", True),
    )
    monkeypatch.setattr(air_module.settings, "openweather_api_key", "test-key")

    record = air_module.fetch_air_pollution_history(
        raw_dir=tmp_path,
        city="Toronto",
        country_code="CA",
        lat=43.6535,
        lon=-79.3839,
        start=start,
        end=end,
        run_id="20250405T000000Z",
    )

    assert record.record_count == 1
    assert called["value"] is False
