from __future__ import annotations
from dataclasses import dataclass
import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

from ..common.config import settings


@dataclass(frozen=True)
class CitySpec:
    city: str
    country_code: str
    state: str | None = None


@dataclass(frozen=True)
class CitySeedResult:
    inserted: int
    skipped_existing: int
    skipped_invalid: int


def _normalize_text(value: object) -> str | None:
    if pd.isna(value):
        return None

    text = str(value).strip()
    return text or None


def _validate_cities_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"CITIES_FILE path does not exist: {path}")

    if not path.is_file():
        raise ValueError(f"CITIES_FILE path is not a file: {path}")

    if not os.access(path, os.R_OK):
        raise PermissionError(f"CITIES_FILE path is not readable: {path}")


def _build_postgres_engine():
    return create_engine(settings.postgres_sqlalchemy_url)


def _parse_cities_dataframe(df: pd.DataFrame) -> tuple[list[CitySpec], int]:
    if "city" not in df.columns or "country_code" not in df.columns:
        raise ValueError("cities.csv must include columns: city,country_code,(optional)state")

    cities: list[CitySpec] = []
    skipped_invalid = 0
    seen: set[tuple[str, str, str | None]] = set()

    for _, r in df.iterrows():
        city = _normalize_text(r["city"])
        cc = _normalize_text(r["country_code"])
        state = _normalize_text(r["state"]) if "state" in df.columns else None
        if city is None or cc is None:
            skipped_invalid += 1
            continue

        ident = (city, cc, state)
        if ident in seen:
            continue

        seen.add(ident)
        cities.append(CitySpec(city=city, country_code=cc, state=state))

    return cities, skipped_invalid


def read_cities_file(path: Path) -> list[CitySpec]:
    _validate_cities_file(path)
    df = pd.read_csv(path)
    cities, _ = _parse_cities_dataframe(df)
    return cities


def seed_cities_from_file(path: Path) -> CitySeedResult:
    _validate_cities_file(path)
    df = pd.read_csv(path)
    cities, skipped_invalid = _parse_cities_dataframe(df)

    inserted = 0
    skipped_existing = 0
    engine = _build_postgres_engine()

    with engine.begin() as connection:
        existing_rows = connection.execute(
            text("SELECT city, country_code, state FROM cities")
        ).fetchall()
        existing = {(row[0], row[1], row[2]) for row in existing_rows}

        for city in cities:
            ident = (city.city, city.country_code, city.state)
            if ident in existing:
                skipped_existing += 1
                continue

            connection.execute(
                text(
                    """
                    INSERT INTO cities (city, country_code, state, is_active)
                    VALUES (:city, :country_code, :state, true)
                    """
                ),
                {
                    "city": city.city,
                    "country_code": city.country_code,
                    "state": city.state,
                },
            )
            existing.add(ident)
            inserted += 1

    return CitySeedResult(
        inserted=inserted,
        skipped_existing=skipped_existing,
        skipped_invalid=skipped_invalid,
    )


def read_cities_from_db() -> list[CitySpec]:
    engine = _build_postgres_engine()
    with engine.begin() as connection:
        rows = connection.execute(
            text(
                """
                SELECT city, country_code, state
                FROM cities
                WHERE is_active = true
                ORDER BY id
                """
            )
        ).fetchall()

    return [CitySpec(city=row[0], country_code=row[1], state=row[2]) for row in rows]


def read_cities(path: Path | None = None) -> list[CitySpec]:
    if settings.cities_source == "postgres":
        return read_cities_from_db()

    if settings.cities_source == "file":
        if path is None:
            raise ValueError("A file path is required when CITIES_SOURCE=file")
        return read_cities_file(path)

    raise ValueError("CITIES_SOURCE must be one of: postgres,file")
