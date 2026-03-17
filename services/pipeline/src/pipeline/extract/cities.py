from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import pandas as pd


@dataclass(frozen=True)
class CitySpec:
    city: str
    country_code: str
    state: str | None = None


def _normalize_text(value: object) -> str | None:
    if pd.isna(value):
        return None

    text = str(value).strip()
    return text or None


def read_cities(path: Path) -> list[CitySpec]:
    df = pd.read_csv(path)
    if "city" not in df.columns or "country_code" not in df.columns:
        raise ValueError("cities.csv must include columns: city,country_code,(optional)state")

    cities: list[CitySpec] = []
    for _, r in df.iterrows():
        city = _normalize_text(r["city"])
        cc = _normalize_text(r["country_code"])
        state = _normalize_text(r["state"]) if "state" in df.columns else None
        if city is None or cc is None:
            continue
        cities.append(CitySpec(city=city, country_code=cc, state=state))
    return cities
