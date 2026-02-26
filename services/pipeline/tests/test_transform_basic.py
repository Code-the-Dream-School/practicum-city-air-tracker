from pathlib import Path
import json
from datetime import datetime, timezone
import pandas as pd

from src.pipeline.transform.openweather_air_pollution_transform import build_gold_from_raw


def test_build_gold_from_raw_parses_list(tmp_path: Path):
    # minimal fake response
    payload = {
        "list": [
            {
                "dt": int(datetime(2025, 1, 1, tzinfo=timezone.utc).timestamp()),
                "main": {"aqi": 2},
                "components": {"pm2_5": 10.0, "pm10": 20.0, "co": 100.0, "no": 0.1, "no2": 0.2, "o3": 3.0, "so2": 1.0, "nh3": 0.5},
            }
        ]
    }
    # mimic expected path layout .../history/<geo_id>/<file>.json
    geo_id = "TestCity,TC:1.0000,2.0000"
    p = tmp_path / "openweather" / "air_pollution" / "history" / geo_id / "x.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload), encoding="utf-8")

    df = build_gold_from_raw([p])
    assert len(df) == 1
    assert "risk_score" in df.columns
    assert df.loc[df.index[0], "aqi_category"] in {"Good","Fair","Moderate","Poor","Very Poor","Unknown"}
