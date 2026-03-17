from pathlib import Path

import pandas as pd
import pytest

from src.pipeline.extract.cities import CitySpec, read_cities


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

    cities = read_cities(path)

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

    cities = read_cities(path)

    assert cities == [CitySpec(city="Lagos", country_code="NG", state=None)]


def test_read_cities_raises_for_missing_required_columns(tmp_path: Path):
    path = tmp_path / "cities.csv"
    pd.DataFrame(
        [
            {"city": "Toronto", "state": "ON"},
        ]
    ).to_csv(path, index=False)

    with pytest.raises(ValueError, match=r"cities\.csv must include columns"):
        read_cities(path)