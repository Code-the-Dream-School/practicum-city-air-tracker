from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import pandas as pd


@dataclass(frozen=True)
class CitySpec:
    city: str
    country_code: str
    state: str | None = None


def read_cities(path: Path) -> list[CitySpec]:
    df = pd.read_csv(path)
    if "city" not in df.columns or "country_code" not in df.columns:
        raise ValueError("cities.csv must include columns: city,country_code,(optional)state")

    cities: list[CitySpec] = []
    for _, r in df.iterrows():
        city = str(r["city"]).strip()
        cc = str(r["country_code"]).strip()
        state = str(r["state"]).strip() if "state" in df.columns and pd.notna(r["state"]) and str(r["state"]).strip() else None
        if not city or not cc:
            continue
        cities.append(CitySpec(city=city, country_code=cc, state=state))
    return cities
