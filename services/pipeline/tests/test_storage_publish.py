from pathlib import Path

import pandas as pd
import pytest

import pipeline.load.storage as storage


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

    def fake_to_sql(self, name, con, if_exists, index):
        captured["sql"] = {
            "name": name,
            "engine_type": type(con).__name__,
            "if_exists": if_exists,
            "index": index,
        }

    monkeypatch.setattr(storage, "_build_postgres_engine", fake_build_postgres_engine)
    monkeypatch.setattr(pd.DataFrame, "to_sql", fake_to_sql, raising=False)

    result = storage.publish_outputs(
        gold_df=pd.DataFrame([{"geo_id": "Toronto,CA", "ts": "2026-04-05T00:00:00Z"}]),
        gold_dir=tmp_path,
        table_name="air_pollution_gold",
    )

    assert captured["engine_built"] is True
    assert captured["sql"] == {
        "name": "air_pollution_gold",
        "engine_type": "DummyEngine",
        "if_exists": "replace",
        "index": False,
    }
    assert result.table_name == "air_pollution_gold"
    assert result.gold_path is None
    assert result.rows == 1


def test_publish_outputs_requires_at_least_one_target(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    monkeypatch.setattr(storage.settings, "use_postgres", False)
    monkeypatch.setattr(storage.settings, "write_gold_parquet", False)

    with pytest.raises(ValueError, match=r"At least one load target must be enabled"):
        storage.publish_outputs(
            gold_df=pd.DataFrame([{"geo_id": "Toronto,CA", "ts": "2026-04-05T00:00:00Z"}]),
            gold_dir=tmp_path,
            table_name="air_pollution_gold",
        )
