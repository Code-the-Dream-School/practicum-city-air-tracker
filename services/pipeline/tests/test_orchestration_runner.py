from pathlib import Path
from types import SimpleNamespace
from typing import Optional

import pandas as pd
import pytest

from pipeline.extract.cities import CitySpec
from pipeline.extract.openweather_air_pollution import RawAirPollutionRecord
from pipeline.load.storage import PublishResult
from pipeline.orchestration import PipelineRunResult, run_pipeline_job
import pipeline.orchestration as orchestration


def test_run_pipeline_job_is_importable_and_returns_result(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    monkeypatch.setattr(orchestration.settings, "cities_file", str(tmp_path / "cities.csv"))
    monkeypatch.setattr(orchestration.settings, "cities_source", "postgres")
    monkeypatch.setattr(orchestration.settings, "raw_dir", str(tmp_path / "raw"))
    monkeypatch.setattr(orchestration.settings, "gold_dir", str(tmp_path / "gold"))

    captured: dict[str, object] = {}
    status_updates: list[object] = []

    def fake_read_cities(path: Optional[Path]) -> list[CitySpec]:
        captured["cities_path"] = path
        return [CitySpec(city="Toronto", country_code="CA", state="ON")]

    def fake_fetch_air_pollution_history(**kwargs):
        captured["fetch_kwargs"] = kwargs
        return RawAirPollutionRecord(
            raw_response_id=1,
            pipeline_run_id=1,
            city_id=1,
            city="Toronto",
            country_code="CA",
            lat=43.6535,
            lon=-79.3839,
            geo_id="Toronto,CA:43.6535,-79.3839",
            request_start_utc=kwargs["start"],
            request_end_utc=kwargs["end"],
            status_code=200,
            record_count=1,
            payload_json={"list": []},
            fetched_at=kwargs["end"],
        )

    def fake_build_gold_from_raw_records(*, raw_records: list[RawAirPollutionRecord]) -> pd.DataFrame:
        captured["raw_records"] = raw_records
        return pd.DataFrame([{"geo_id": "Toronto,CA", "ts": "2026-03-17T00:00:00Z"}])

    def fake_publish_outputs(**kwargs):
        captured["publish_kwargs"] = kwargs
        return PublishResult(
            table_name="air_pollution_gold",
            gold_path=None,
            rows=1,
        )

    monkeypatch.setattr(orchestration, "read_cities", fake_read_cities)
    monkeypatch.setattr(orchestration, "geocode_city", lambda **_: SimpleNamespace(lat=43.6535, lon=-79.3839))
    monkeypatch.setattr(orchestration, "fetch_air_pollution_history", fake_fetch_air_pollution_history)
    monkeypatch.setattr(orchestration, "build_gold_from_raw_records", fake_build_gold_from_raw_records)
    monkeypatch.setattr(orchestration, "publish_outputs", fake_publish_outputs)
    monkeypatch.setattr(orchestration, "create_pipeline_run", lambda **kwargs: 101)
    monkeypatch.setattr(orchestration, "update_pipeline_run_status", lambda run_id, update: status_updates.append((run_id, update)))

    result = run_pipeline_job(source="openweather", history_hours=72)

    assert isinstance(result, PipelineRunResult)
    assert result.pipeline_run_id == 101
    assert result.source == "openweather"
    assert result.history_hours == 72
    assert result.rows == 1
    assert result.gold_path is None
    assert result.azure_blob_path is None
    assert result.postgres_table == "air_pollution_gold"
    assert captured["cities_path"] is None
    assert len(captured["raw_records"]) == 1
    assert captured["raw_records"][0].city == "Toronto"
    assert captured["fetch_kwargs"]["pipeline_run_id"] == 101
    assert isinstance(captured["publish_kwargs"]["gold_df"], pd.DataFrame)
    assert captured["publish_kwargs"]["gold_dir"] == tmp_path / "gold"
    assert captured["publish_kwargs"]["table_name"] == "air_pollution_gold"
    assert len(status_updates) == 1
    assert status_updates[0][0] == result.run_id
    assert status_updates[0][1].status == "succeeded"
    assert status_updates[0][1].city_count == 1
    assert status_updates[0][1].raw_response_count == 1
    assert status_updates[0][1].gold_row_count == 1


def test_run_pipeline_job_fails_fast_when_cities_file_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    missing_path = tmp_path / "missing-cities.csv"

    monkeypatch.setattr(orchestration.settings, "cities_file", str(missing_path))
    monkeypatch.setattr(orchestration.settings, "cities_source", "file")
    monkeypatch.setattr(orchestration.settings, "raw_dir", str(tmp_path / "raw"))
    monkeypatch.setattr(orchestration.settings, "gold_dir", str(tmp_path / "gold"))

    geocode_called = {"value": False}
    status_updates: list[object] = []

    def should_not_be_called(**_):
        geocode_called["value"] = True
        return SimpleNamespace(lat=0.0, lon=0.0)

    monkeypatch.setattr(orchestration, "geocode_city", should_not_be_called)
    monkeypatch.setattr(orchestration, "create_pipeline_run", lambda **kwargs: 202)
    monkeypatch.setattr(orchestration, "update_pipeline_run_status", lambda run_id, update: status_updates.append((run_id, update)))

    with pytest.raises(FileNotFoundError, match=r"CITIES_FILE path does not exist") as error:
        run_pipeline_job()

    assert str(missing_path) in str(error.value)
    assert geocode_called["value"] is False
    assert len(status_updates) == 1
    assert status_updates[0][1].status == "failed"
    assert "CITIES_FILE path does not exist" in status_updates[0][1].error_message
