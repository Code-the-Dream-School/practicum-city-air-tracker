from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from pipeline.extract.cities import CitySpec
from pipeline.orchestration import PipelineRunResult, run_pipeline_job
import pipeline.orchestration as orchestration


def test_run_pipeline_job_is_importable_and_returns_result(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    monkeypatch.setattr(orchestration.settings, "cities_file", str(tmp_path / "cities.csv"))
    monkeypatch.setattr(orchestration.settings, "raw_dir", str(tmp_path / "raw"))
    monkeypatch.setattr(orchestration.settings, "gold_dir", str(tmp_path / "gold"))

    captured: dict[str, object] = {}

    def fake_read_cities(path: Path) -> list[CitySpec]:
        captured["cities_path"] = path
        return [CitySpec(city="Toronto", country_code="CA", state="ON")]

    def fake_fetch_air_pollution_history(**kwargs):
        captured["fetch_kwargs"] = kwargs
        return tmp_path / "raw" / "x.json"

    def fake_build_gold_from_raw(*, raw_files: list[Path]) -> pd.DataFrame:
        captured["raw_files"] = raw_files
        return pd.DataFrame([{"geo_id": "Toronto,CA", "ts": "2026-03-17T00:00:00Z"}])

    def fake_publish_outputs(**kwargs):
        captured["publish_kwargs"] = kwargs
        return tmp_path / "gold" / "air_pollution_gold.parquet"

    monkeypatch.setattr(orchestration, "read_cities", fake_read_cities)
    monkeypatch.setattr(orchestration, "geocode_city", lambda **_: SimpleNamespace(lat=43.6535, lon=-79.3839))
    monkeypatch.setattr(orchestration, "fetch_air_pollution_history", fake_fetch_air_pollution_history)
    monkeypatch.setattr(orchestration, "build_gold_from_raw", fake_build_gold_from_raw)
    monkeypatch.setattr(orchestration, "publish_outputs", fake_publish_outputs)

    result = run_pipeline_job(source="openweather", history_hours=72)

    assert isinstance(result, PipelineRunResult)
    assert result.source == "openweather"
    assert result.history_hours == 72
    assert result.rows == 1
    assert result.gold_path == tmp_path / "gold" / "air_pollution_gold.parquet"
    assert captured["cities_path"] == tmp_path / "cities.csv"
    assert captured["raw_files"] == [tmp_path / "raw" / "x.json"]
    assert isinstance(captured["publish_kwargs"]["gold_df"], pd.DataFrame)
    assert captured["publish_kwargs"]["gold_dir"] == tmp_path / "gold"
    assert captured["publish_kwargs"]["table_name"] == "air_pollution_gold"


def test_run_pipeline_job_fails_fast_when_cities_file_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    missing_path = tmp_path / "missing-cities.csv"

    monkeypatch.setattr(orchestration.settings, "cities_file", str(missing_path))
    monkeypatch.setattr(orchestration.settings, "raw_dir", str(tmp_path / "raw"))
    monkeypatch.setattr(orchestration.settings, "gold_dir", str(tmp_path / "gold"))

    geocode_called = {"value": False}

    def should_not_be_called(**_):
        geocode_called["value"] = True
        return SimpleNamespace(lat=0.0, lon=0.0)

    monkeypatch.setattr(orchestration, "geocode_city", should_not_be_called)

    with pytest.raises(FileNotFoundError, match=r"CITIES_FILE path does not exist") as error:
        run_pipeline_job()

    assert str(missing_path) in str(error.value)
    assert geocode_called["value"] is False
