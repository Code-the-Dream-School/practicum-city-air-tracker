"""Tests for raw_air_pollution repository module."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine

from pipeline.extract.openweather_air_pollution import (
    RawAirPollutionRecord,
    raw_air_pollution_responses_table,
    cities_table,
)
from pipeline.repository.raw_air_pollution import load_raw_responses_by_pipeline_run_id
from pipeline.run_tracking import pipeline_runs_table


@pytest.fixture
def sqlite_engine(tmp_path):
    """Create an in-memory SQLite database for testing."""
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite+pysqlite:///{db_path}")

    # Create tables
    metadata = sa.MetaData()

    sa.Table(
        "cities",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("city", sa.Text(), nullable=False),
        sa.Column("country_code", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=True),
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


def test_load_raw_responses_returns_empty_list_for_missing_pipeline_run(sqlite_engine):
    """When pipeline_run_id doesn't exist, return empty list."""
    with patch("pipeline.repository.raw_air_pollution._build_postgres_engine", return_value=sqlite_engine):
        records = load_raw_responses_by_pipeline_run_id(pipeline_run_id=9999)
        assert records == []


def test_load_raw_responses_by_pipeline_run_id(sqlite_engine):
    """Load raw responses for a pipeline run, joined with city data."""
    now = datetime.now(timezone.utc)

    with sqlite_engine.begin() as connection:
        # Insert test cities
        connection.execute(
            cities_table.insert().values(
                id=1,
                city="Paris",
                country_code="FR",
                state=None,
            )
        )
        connection.execute(
            cities_table.insert().values(
                id=2,
                city="Lagos",
                country_code="NG",
                state=None,
            )
        )

        # Insert pipeline run
        connection.execute(
            pipeline_runs_table.insert().values(
                id=100,
                run_id="test_run_001",
                source="openweather",
                history_hours=72,
                window_start_utc=now - timedelta(hours=72),
                window_end_utc=now,
                status="running",
                started_at=now,
            )
        )

        # Insert raw responses for Paris
        connection.execute(
            raw_air_pollution_responses_table.insert().values(
                pipeline_run_id=100,
                city_id=1,
                geo_id="Paris,FR:48.8589,2.3200",
                lat=48.8589,
                lon=2.3200,
                request_url="https://api.openweathermap.org/data/2.5/air_pollution/history",
                request_start_utc=now - timedelta(hours=72),
                request_end_utc=now,
                status_code=200,
                record_count=5,
                payload_json={"list": [{"dt": 1000000, "main": {"aqi": 2}}]},
                fetched_at=now,
            )
        )

        # Insert raw responses for Lagos
        connection.execute(
            raw_air_pollution_responses_table.insert().values(
                pipeline_run_id=100,
                city_id=2,
                geo_id="Lagos,NG:6.4551,3.3942",
                lat=6.4551,
                lon=3.3942,
                request_url="https://api.openweathermap.org/data/2.5/air_pollution/history",
                request_start_utc=now - timedelta(hours=72),
                request_end_utc=now,
                status_code=200,
                record_count=3,
                payload_json={"list": [{"dt": 2000000, "main": {"aqi": 3}}]},
                fetched_at=now,
            )
        )

    # Load the records using mocked engine
    with patch("pipeline.repository.raw_air_pollution._build_postgres_engine", return_value=sqlite_engine):
        records = load_raw_responses_by_pipeline_run_id(pipeline_run_id=100)

    # Verify results
    assert len(records) == 2
    assert all(isinstance(r, RawAirPollutionRecord) for r in records)

    # Check first record (Paris, ordered by city_id)
    paris_record = records[0]
    assert paris_record.city == "Paris"
    assert paris_record.country_code == "FR"
    assert paris_record.city_id == 1
    assert paris_record.lat == 48.8589
    assert paris_record.lon == 2.3200
    assert paris_record.status_code == 200
    assert paris_record.record_count == 5
    assert paris_record.payload_json == {"list": [{"dt": 1000000, "main": {"aqi": 2}}]}

    # Check second record (Lagos)
    lagos_record = records[1]
    assert lagos_record.city == "Lagos"
    assert lagos_record.country_code == "NG"
    assert lagos_record.city_id == 2
    assert lagos_record.lat == 6.4551
    assert lagos_record.lon == 3.3942
    assert lagos_record.status_code == 200
    assert lagos_record.record_count == 3


def test_load_raw_responses_deserializes_json_string_payload(sqlite_engine):
    """If payload_json is stored as string, deserialize it."""
    now = datetime.now(timezone.utc)

    with sqlite_engine.begin() as connection:
        connection.execute(
            cities_table.insert().values(
                id=1,
                city="Test City",
                country_code="TC",
            )
        )

        connection.execute(
            pipeline_runs_table.insert().values(
                id=101,
                run_id="test_run_002",
                source="openweather",
                history_hours=72,
                window_start_utc=now - timedelta(hours=72),
                window_end_utc=now,
                status="running",
                started_at=now,
            )
        )

        # Insert with JSON string (simulates certain DB drivers)
        connection.execute(
            raw_air_pollution_responses_table.insert().values(
                pipeline_run_id=101,
                city_id=1,
                geo_id="Test,TC:0.0,0.0",
                lat=0.0,
                lon=0.0,
                request_url="https://api.openweathermap.org/data/2.5/air_pollution/history",
                request_start_utc=now,
                request_end_utc=now,
                status_code=200,
                record_count=1,
                payload_json='{"list": [{"dt": 1000, "main": {"aqi": 1}}]}',
                fetched_at=now,
            )
        )

    with patch("pipeline.repository.raw_air_pollution._build_postgres_engine", return_value=sqlite_engine):
        records = load_raw_responses_by_pipeline_run_id(pipeline_run_id=101)

    assert len(records) == 1
    assert isinstance(records[0].payload_json, dict)
    assert records[0].payload_json == {"list": [{"dt": 1000, "main": {"aqi": 1}}]}


def test_load_raw_responses_handles_null_payload_gracefully(sqlite_engine):
    """If payload_json can't be deserialized, use empty dict."""
    now = datetime.now(timezone.utc)

    with sqlite_engine.begin() as connection:
        connection.execute(
            cities_table.insert().values(
                id=1,
                city="Test City",
                country_code="TC",
            )
        )

        connection.execute(
            pipeline_runs_table.insert().values(
                id=102,
                run_id="test_run_003",
                source="openweather",
                history_hours=72,
                window_start_utc=now - timedelta(hours=72),
                window_end_utc=now,
                status="running",
                started_at=now,
            )
        )

        # Insert with invalid JSON string
        connection.execute(
            raw_air_pollution_responses_table.insert().values(
                pipeline_run_id=102,
                city_id=1,
                geo_id="Test,TC:0.0,0.0",
                lat=0.0,
                lon=0.0,
                request_url="https://api.openweathermap.org/data/2.5/air_pollution/history",
                request_start_utc=now,
                request_end_utc=now,
                status_code=200,
                record_count=0,
                payload_json='{"invalid json}',  # Malformed JSON
                fetched_at=now,
            )
        )

    with patch("pipeline.repository.raw_air_pollution._build_postgres_engine", return_value=sqlite_engine):
        records = load_raw_responses_by_pipeline_run_id(pipeline_run_id=102)

    assert len(records) == 1
    assert records[0].payload_json == {}
