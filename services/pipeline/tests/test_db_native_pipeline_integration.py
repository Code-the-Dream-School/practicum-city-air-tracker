from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine, text
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

import pipeline.extract.cities as cities_module
import pipeline.extract.geocoding as geocoding_module
import pipeline.extract.openweather_air_pollution as air_module
import pipeline.load.storage as storage_module
import pipeline.orchestration as orchestration
import pipeline.run_tracking as run_tracking


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
        sa.UniqueConstraint("city", "country_code", "state", name="uq_cities_city_country_state"),
    )
    sa.Table(
        "geocoding_cache",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("city_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("lat", sa.Numeric(9, 6), nullable=False),
        sa.Column("lon", sa.Numeric(9, 6), nullable=False),
        sa.Column("provider_name", sa.Text(), nullable=True),
        sa.Column("provider_state", sa.Text(), nullable=True),
        sa.Column("provider_country", sa.Text(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.Column("city_count", sa.Integer(), nullable=True),
        sa.Column("raw_response_count", sa.Integer(), nullable=True),
        sa.Column("gold_row_count", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.UniqueConstraint(
            "city_id",
            "request_start_utc",
            "request_end_utc",
            name="uq_raw_air_pollution_city_window",
        ),
    )
    sa.Table(
        "air_pollution_gold",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("pipeline_run_id", sa.Integer(), nullable=False),
        sa.Column("raw_response_id", sa.Integer(), nullable=True),
        sa.Column("city_id", sa.Integer(), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("city", sa.Text(), nullable=False),
        sa.Column("country_code", sa.Text(), nullable=False),
        sa.Column("lat", sa.Numeric(9, 6), nullable=False),
        sa.Column("lon", sa.Numeric(9, 6), nullable=False),
        sa.Column("geo_id", sa.Text(), nullable=False),
        sa.Column("aqi", sa.Integer(), nullable=True),
        sa.Column("co", sa.Numeric(12, 4), nullable=True),
        sa.Column("no", sa.Numeric(12, 4), nullable=True),
        sa.Column("no2", sa.Numeric(12, 4), nullable=True),
        sa.Column("o3", sa.Numeric(12, 4), nullable=True),
        sa.Column("so2", sa.Numeric(12, 4), nullable=True),
        sa.Column("nh3", sa.Numeric(12, 4), nullable=True),
        sa.Column("pm2_5", sa.Numeric(12, 4), nullable=True),
        sa.Column("pm10", sa.Numeric(12, 4), nullable=True),
        sa.Column("pm2_5_24h_avg", sa.Numeric(12, 4), nullable=True),
        sa.Column("aqi_category", sa.Text(), nullable=False),
        sa.Column("risk_score", sa.Numeric(12, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("geo_id", "ts", name="uq_air_pollution_gold_geo_id_ts"),
    )

    metadata.create_all(engine)
    return engine


def _seed_city(engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO cities (city, country_code, state, is_active)
                VALUES ('Toronto', 'CA', 'ON', 1)
                """
            )
        )


@pytest.fixture
def db_native_pipeline(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    engine = _build_sqlite_engine(tmp_path / "db-native-pipeline.db")
    _seed_city(engine)

    start = datetime(2026, 4, 5, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 4, 8, 0, 0, tzinfo=timezone.utc)

    for module in (
        cities_module,
        geocoding_module,
        air_module,
        run_tracking,
        storage_module,
    ):
        monkeypatch.setattr(module, "_build_postgres_engine", lambda engine=engine: engine)

    monkeypatch.setattr(storage_module, "pg_insert", sqlite_insert)
    monkeypatch.setattr(orchestration, "build_runtime_window", lambda history_hours: (start, end))
    monkeypatch.setattr(orchestration.settings, "cities_source", "postgres")
    monkeypatch.setattr(orchestration.settings, "raw_dir", str(tmp_path / "raw"))
    monkeypatch.setattr(orchestration.settings, "gold_dir", str(tmp_path / "gold"))
    monkeypatch.setattr(orchestration.settings, "use_postgres", True)
    monkeypatch.setattr(orchestration.settings, "write_gold_parquet", False)
    monkeypatch.setattr(geocoding_module.settings, "openweather_api_key", "test-key")
    monkeypatch.setattr(air_module.settings, "openweather_api_key", "test-key")
    monkeypatch.setattr(geocoding_module._limiter, "wait", lambda: None)
    monkeypatch.setattr(air_module._limiter, "wait", lambda: None)

    now_values = iter(
        [
            datetime(2026, 4, 5, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 4, 5, 0, 1, tzinfo=timezone.utc),
            datetime(2026, 4, 5, 0, 2, tzinfo=timezone.utc),
            datetime(2026, 4, 5, 0, 3, tzinfo=timezone.utc),
            datetime(2026, 4, 5, 0, 4, tzinfo=timezone.utc),
            datetime(2026, 4, 5, 0, 5, tzinfo=timezone.utc),
        ]
    )

    class FixedDateTime:
        @classmethod
        def now(cls, tz=None):
            value = next(now_values)
            if tz is None:
                return value.replace(tzinfo=None)
            return value.astimezone(tz)

    monkeypatch.setattr(orchestration, "datetime", FixedDateTime)

    class DummyGeoResponse:
        def json(self):
            return [
                {
                    "lat": 43.6535,
                    "lon": -79.3839,
                    "name": "Toronto",
                    "state": "Ontario",
                    "country": "CA",
                }
            ]

    class DummyAirResponse:
        status_code = 200

        def json(self):
            return {
                "list": [
                    {
                        "dt": int(datetime(2026, 4, 5, 0, 0, tzinfo=timezone.utc).timestamp()),
                        "main": {"aqi": 2},
                        "components": {"pm2_5": 10.0, "pm10": 20.0, "co": 100.0},
                    },
                    {
                        "dt": int(datetime(2026, 4, 5, 1, 0, tzinfo=timezone.utc).timestamp()),
                        "main": {"aqi": 3},
                        "components": {"pm2_5": 11.0, "pm10": 21.0, "co": 101.0},
                    },
                ]
            }

    monkeypatch.setattr(geocoding_module, "get_with_retries", lambda *args, **kwargs: DummyGeoResponse())
    monkeypatch.setattr(air_module, "get_with_retries", lambda *args, **kwargs: DummyAirResponse())

    return engine


def test_run_pipeline_job_persists_db_native_success_flow(db_native_pipeline):
    result = orchestration.run_pipeline_job(source="openweather", history_hours=72)

    assert result.postgres_table == "air_pollution_gold"
    assert result.gold_path is None
    assert result.rows == 2

    with db_native_pipeline.begin() as connection:
        run_row = connection.execute(
            text(
                """
                SELECT status, city_count, raw_response_count, gold_row_count
                FROM pipeline_runs
                ORDER BY id
                LIMIT 1
                """
            )
        ).fetchone()
        geocode_count = connection.execute(text("SELECT COUNT(*) FROM geocoding_cache")).scalar_one()
        raw_count = connection.execute(text("SELECT COUNT(*) FROM raw_air_pollution_responses")).scalar_one()
        gold_count = connection.execute(text("SELECT COUNT(*) FROM air_pollution_gold")).scalar_one()

    assert run_row == ("succeeded", 1, 1, 2)
    assert geocode_count == 1
    assert raw_count == 1
    assert gold_count == 2


def test_rerun_reuses_raw_response_and_upserts_gold_rows(db_native_pipeline):
    first_result = orchestration.run_pipeline_job(source="openweather", history_hours=72)
    second_result = orchestration.run_pipeline_job(source="openweather", history_hours=72)

    with db_native_pipeline.begin() as connection:
        run_count = connection.execute(text("SELECT COUNT(*) FROM pipeline_runs")).scalar_one()
        raw_count = connection.execute(text("SELECT COUNT(*) FROM raw_air_pollution_responses")).scalar_one()
        gold_count = connection.execute(text("SELECT COUNT(*) FROM air_pollution_gold")).scalar_one()
        latest_gold_run_id = connection.execute(
            text(
                """
                SELECT DISTINCT pipeline_run_id
                FROM air_pollution_gold
                ORDER BY pipeline_run_id DESC
                LIMIT 1
                """
            )
        ).scalar_one()

    assert first_result.rows == 2
    assert second_result.rows == 2
    assert run_count == 2
    assert raw_count == 1
    assert gold_count == 2
    assert latest_gold_run_id == second_result.pipeline_run_id


def test_failed_load_persists_failed_pipeline_run_status(db_native_pipeline, monkeypatch: pytest.MonkeyPatch):
    def raise_publish_error(**kwargs):
        raise RuntimeError("gold load failed")

    monkeypatch.setattr(orchestration, "publish_outputs", raise_publish_error)

    with pytest.raises(RuntimeError, match="gold load failed"):
        orchestration.run_pipeline_job(source="openweather", history_hours=72)

    with db_native_pipeline.begin() as connection:
        row = connection.execute(
            text(
                """
                SELECT status, error_message
                FROM pipeline_runs
                ORDER BY id DESC
                LIMIT 1
                """
            )
        ).fetchone()

    assert row == ("failed", "gold load failed")
