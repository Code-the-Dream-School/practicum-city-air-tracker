from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

import pipeline.extract.geocoding as geocoding


def _build_sqlite_engine(db_path: Path):
    engine = create_engine(f"sqlite+pysqlite:///{db_path}")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE cities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    city TEXT NOT NULL,
                    country_code TEXT NOT NULL,
                    state TEXT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT 1
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE geocoding_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    city_id INTEGER NOT NULL UNIQUE,
                    query_text TEXT NOT NULL,
                    lat NUMERIC NOT NULL,
                    lon NUMERIC NOT NULL,
                    provider_name TEXT NULL,
                    provider_state TEXT NULL,
                    provider_country TEXT NULL,
                    fetched_at TEXT NOT NULL,
                    created_at TEXT NULL
                )
                """
            )
        )
    return engine


def test_geocode_city_uses_postgres_cache_hit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    engine = _build_sqlite_engine(tmp_path / "geo-cache-hit.db")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO cities (city, country_code, state, is_active)
                VALUES ('Toronto', 'CA', 'ON', 1)
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO geocoding_cache (
                    city_id,
                    query_text,
                    lat,
                    lon,
                    provider_name,
                    provider_state,
                    provider_country,
                    fetched_at
                )
                VALUES (1, 'Toronto,ON,CA', 43.6535, -79.3839, 'Toronto', 'Ontario', 'CA', '2026-04-05T00:00:00Z')
                """
            )
        )

    called = {"value": False}
    monkeypatch.setattr(geocoding, "_build_postgres_engine", lambda: engine)
    monkeypatch.setattr(geocoding._limiter, "wait", lambda: None)
    monkeypatch.setattr(
        geocoding,
        "get_with_retries",
        lambda *args, **kwargs: called.__setitem__("value", True),
    )

    coords = geocoding.geocode_city(
        raw_dir=tmp_path,
        city="Toronto",
        country_code="CA",
        state="ON",
    )

    assert coords == geocoding.Coords(lat=43.6535, lon=-79.3839)
    assert called["value"] is False


def test_geocode_city_writes_postgres_cache_on_miss(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    engine = _build_sqlite_engine(tmp_path / "geo-cache-miss.db")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO cities (city, country_code, state, is_active)
                VALUES ('Paris', 'FR', NULL, 1)
                """
            )
        )

    class DummyResponse:
        status_code = 200

        def json(self):
            return [
                {
                    "lat": 48.8566,
                    "lon": 2.3522,
                    "name": "Paris",
                    "state": None,
                    "country": "FR",
                }
            ]

    monkeypatch.setattr(geocoding, "_build_postgres_engine", lambda: engine)
    monkeypatch.setattr(geocoding._limiter, "wait", lambda: None)
    monkeypatch.setattr(geocoding, "get_with_retries", lambda *args, **kwargs: DummyResponse())
    monkeypatch.setattr(geocoding.settings, "openweather_api_key", "test-key")

    coords = geocoding.geocode_city(
        raw_dir=tmp_path,
        city="Paris",
        country_code="FR",
        state=None,
    )

    assert coords == geocoding.Coords(lat=48.8566, lon=2.3522)

    with engine.begin() as connection:
        row = connection.execute(
            text(
                """
                SELECT query_text, lat, lon, provider_name, provider_country
                FROM geocoding_cache
                WHERE city_id = 1
                """
            )
        ).fetchone()

    assert row is not None
    assert row[0] == "Paris,FR"
    assert float(row[1]) == 48.8566
    assert float(row[2]) == 2.3522
    assert row[3] == "Paris"
    assert row[4] == "FR"


def test_lookup_city_id_handles_null_state(tmp_path: Path):
    engine = _build_sqlite_engine(tmp_path / "geo-null-state.db")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO cities (city, country_code, state, is_active)
                VALUES ('Paris', 'FR', NULL, 1)
                """
            )
        )

        assert geocoding._lookup_city_id(connection, city="Paris", country_code="FR", state=None) == 1


def test_lookup_city_id_handles_non_null_state(tmp_path: Path):
    engine = _build_sqlite_engine(tmp_path / "geo-state.db")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO cities (city, country_code, state, is_active)
                VALUES ('Toronto', 'CA', 'ON', 1)
                """
            )
        )

        assert geocoding._lookup_city_id(connection, city="Toronto", country_code="CA", state="ON") == 1
