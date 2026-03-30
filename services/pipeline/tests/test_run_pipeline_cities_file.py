
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

import run_pipeline
from src.pipeline.extract.cities import CitySpec


def test_main_honors_configured_cities_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    cities_path = tmp_path / "custom-cities.csv"
    cities_path.write_text("city,country_code,state\nToronto,CA,ON\n", encoding="utf-8")

    monkeypatch.setattr(run_pipeline.settings, "cities_file", str(cities_path))
    monkeypatch.setattr(run_pipeline.settings, "raw_dir", str(tmp_path / "raw"))
    monkeypatch.setattr(run_pipeline.settings, "gold_dir", str(tmp_path / "gold"))

    monkeypatch.setattr(
        run_pipeline.argparse.ArgumentParser,
        "parse_args",
        lambda self: Namespace(source="openweather", history_hours=72),
    )

    captured: dict[str, Path] = {}

    def fake_read_cities(path: Path) -> list[CitySpec]:
        captured["path"] = path
        return [CitySpec(city="Toronto", country_code="CA", state="ON")]

    monkeypatch.setattr(run_pipeline, "read_cities", fake_read_cities)
    monkeypatch.setattr(run_pipeline, "geocode_city", lambda **_: SimpleNamespace(lat=43.6535, lon=-79.3839))
    monkeypatch.setattr(run_pipeline, "fetch_air_pollution_history", lambda **_: tmp_path / "raw" / "x.json")
    monkeypatch.setattr(run_pipeline, "build_gold_from_raw", lambda **_: pd.DataFrame([{"geo_id": "Toronto,CA", "ts": "2026-03-17T00:00:00Z"}]))
    monkeypatch.setattr(run_pipeline, "publish_outputs", lambda **_: tmp_path / "gold" / "air_pollution_gold.parquet")

    run_pipeline.main()

    assert captured["path"] == cities_path


def test_main_fails_fast_when_cities_file_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    missing_path = tmp_path / "missing-cities.csv"

    monkeypatch.setattr(run_pipeline.settings, "cities_file", str(missing_path))
    monkeypatch.setattr(run_pipeline.settings, "raw_dir", str(tmp_path / "raw"))
    monkeypatch.setattr(run_pipeline.settings, "gold_dir", str(tmp_path / "gold"))

    monkeypatch.setattr(
        run_pipeline.argparse.ArgumentParser,
        "parse_args",
        lambda self: Namespace(source="openweather", history_hours=72),
    )

    geocode_called = {"value": False}

    def should_not_be_called(**_):
        geocode_called["value"] = True
        return SimpleNamespace(lat=0.0, lon=0.0)

    monkeypatch.setattr(run_pipeline, "geocode_city", should_not_be_called)

    with pytest.raises(FileNotFoundError, match=r"CITIES_FILE path does not exist") as error:
        run_pipeline.main()

    assert str(missing_path) in str(error.value)
    assert geocode_called["value"] is False
