from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy.dialects import postgresql

import pipeline.load.storage as storage


def build_gold_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "pipeline_run_id": 1,
                "raw_response_id": 10,
                "city_id": 7,
                "ts": pd.Timestamp("2026-04-05T00:00:00Z"),
                "city": "Toronto",
                "country_code": "CA",
                "lat": 43.6535,
                "lon": -79.3839,
                "geo_id": "Toronto,CA:43.6535,-79.3839",
                "aqi": 2,
                "pm2_5": 10.0,
                "pm2_5_24h_avg": 10.0,
                "aqi_category": "Fair",
                "risk_score": 1.2,
            }
        ]
    )


def test_publish_outputs_supports_postgres_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    monkeypatch.setattr(storage.settings, "use_postgres", True)
    monkeypatch.setattr(storage.settings, "write_gold_parquet", False)

    captured: dict[str, object] = {}

    class DummyEngine:
        pass

    def fake_build_postgres_engine():
        captured["engine_built"] = True
        return DummyEngine()

    def fake_upsert_gold_rows(*, engine, gold_df, table_name):
        captured["upsert"] = {
            "engine_type": type(engine).__name__,
            "table_name": table_name,
            "rows": len(gold_df),
        }

    monkeypatch.setattr(storage, "_build_postgres_engine", fake_build_postgres_engine)
    monkeypatch.setattr(storage, "_upsert_gold_rows", fake_upsert_gold_rows)

    result = storage.publish_outputs(
        gold_df=build_gold_df(),
        gold_dir=tmp_path,
        table_name="air_pollution_gold",
    )

    assert captured["engine_built"] is True
    assert captured["upsert"] == {
        "engine_type": "DummyEngine",
        "table_name": "air_pollution_gold",
        "rows": 1,
    }
    assert result.table_name == "air_pollution_gold"
    assert result.gold_path is None
    assert result.rows == 1


def test_prepare_gold_rows_requires_lineage_columns():
    gold_df = pd.DataFrame(
        [
            {
                "ts": pd.Timestamp("2026-04-05T00:00:00Z"),
                "city": "Toronto",
                "country_code": "CA",
                "lat": 43.6535,
                "lon": -79.3839,
                "geo_id": "Toronto,CA:43.6535,-79.3839",
                "aqi_category": "Fair",
            }
        ]
    )

    with pytest.raises(ValueError, match=r"Gold DataFrame is missing required PostgreSQL columns"):
        storage._prepare_gold_rows(gold_df)


def test_build_gold_upsert_statement_targets_geo_id_and_ts():
    statement = storage._build_gold_upsert_statement(
        "air_pollution_gold",
        storage._prepare_gold_rows(build_gold_df()),
    )
    compiled = str(statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))

    assert "ON CONFLICT (geo_id, ts) DO UPDATE SET" in compiled
    assert "pipeline_run_id = excluded.pipeline_run_id" in compiled
    assert "raw_response_id = excluded.raw_response_id" in compiled
    assert "updated_at = now()" in compiled


def test_publish_outputs_requires_at_least_one_target(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    monkeypatch.setattr(storage.settings, "use_postgres", False)
    monkeypatch.setattr(storage.settings, "write_gold_parquet", False)

    with pytest.raises(ValueError, match=r"At least one load target must be enabled"):
        storage.publish_outputs(
            gold_df=build_gold_df(),
            gold_dir=tmp_path,
            table_name="air_pollution_gold",
        )
