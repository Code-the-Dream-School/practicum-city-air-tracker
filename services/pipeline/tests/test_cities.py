from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine, text

import pipeline.extract.cities as cities_module
from pipeline.extract.cities import CitySeedResult, CitySpec, read_cities, read_cities_file, read_cities_from_db, seed_cities_from_file


def test_read_cities_skips_blank_required_values(tmp_path: Path):
    path = tmp_path / "cities.csv"
    pd.DataFrame(
        [
            {"city": "Toronto", "country_code": "CA", "state": "ON"},
            {"city": "", "country_code": "US", "state": "CA"},
            {"city": "   ", "country_code": "GB", "state": ""},
            {"city": "Paris", "country_code": "   ", "state": None},
        ]
    ).to_csv(path, index=False)

    cities = read_cities_file(path)

    assert cities == [CitySpec(city="Toronto", country_code="CA", state="ON")]


def test_read_cities_skips_nan_required_values(tmp_path: Path):
    path = tmp_path / "cities.csv"
    pd.DataFrame(
        [
            {"city": "Lagos", "country_code": "NG", "state": pd.NA},
            {"city": pd.NA, "country_code": "AU", "state": "NSW"},
            {"city": "Sydney", "country_code": float("nan"), "state": "NSW"},
        ]
    ).to_csv(path, index=False)

    cities = read_cities_file(path)

    assert cities == [CitySpec(city="Lagos", country_code="NG", state=None)]


def test_read_cities_raises_for_missing_required_columns(tmp_path: Path):
    path = tmp_path / "cities.csv"
    pd.DataFrame(
        [
            {"city": "Toronto", "state": "ON"},
        ]
    ).to_csv(path, index=False)

    with pytest.raises(ValueError, match=r"cities\.csv must include columns"):
        read_cities_file(path)


def test_read_cities_raises_clear_error_for_missing_file(tmp_path: Path):
    path = tmp_path / "does-not-exist.csv"

    with pytest.raises(FileNotFoundError, match=r"CITIES_FILE path does not exist") as error:
        read_cities_file(path)

    assert str(path) in str(error.value)


def test_seed_cities_from_file_is_idempotent(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    path = tmp_path / "cities.csv"
    pd.DataFrame(
        [
            {"city": "Toronto", "country_code": "CA", "state": "ON"},
            {"city": "Toronto", "country_code": "CA", "state": "ON"},
            {"city": "Paris", "country_code": "FR", "state": None},
            {"city": "", "country_code": "US", "state": "CA"},
        ]
    ).to_csv(path, index=False)

    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'cities.db'}")
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

    monkeypatch.setattr(cities_module, "_build_postgres_engine", lambda: engine)

    first = seed_cities_from_file(path)
    second = seed_cities_from_file(path)

    assert first == CitySeedResult(inserted=2, skipped_existing=0, skipped_invalid=1)
    assert second == CitySeedResult(inserted=0, skipped_existing=2, skipped_invalid=1)


def test_read_cities_from_db_returns_active_rows(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'cities_read.db'}")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE cities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    city TEXT NOT NULL,
                    country_code TEXT NOT NULL,
                    state TEXT NULL,
                    is_active BOOLEAN NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO cities (city, country_code, state, is_active)
                VALUES
                    ('Toronto', 'CA', 'ON', 1),
                    ('Paris', 'FR', NULL, 1),
                    ('Inactive City', 'US', NULL, 0)
                """
            )
        )

    monkeypatch.setattr(cities_module, "_build_postgres_engine", lambda: engine)

    assert read_cities_from_db() == [
        CitySpec(city="Toronto", country_code="CA", state="ON"),
        CitySpec(city="Paris", country_code="FR", state=None),
    ]


def test_read_cities_routes_to_postgres_by_default(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(cities_module.settings, "cities_source", "postgres")
    monkeypatch.setattr(
        cities_module,
        "read_cities_from_db",
        lambda: [CitySpec(city="Toronto", country_code="CA", state="ON")],
    )

    assert read_cities() == [CitySpec(city="Toronto", country_code="CA", state="ON")]
