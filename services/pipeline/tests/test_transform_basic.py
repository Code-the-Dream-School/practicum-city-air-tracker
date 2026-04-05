from datetime import datetime, timezone

from pipeline.extract.openweather_air_pollution import RawAirPollutionRecord
from pipeline.transform.openweather_air_pollution_transform import build_gold_from_raw_records


def test_build_gold_from_raw_records_parses_list():
    payload = {
        "list": [
            {
                "dt": int(datetime(2025, 1, 1, tzinfo=timezone.utc).timestamp()),
                "main": {"aqi": 2},
                "components": {"pm2_5": 10.0, "pm10": 20.0, "co": 100.0, "no": 0.1, "no2": 0.2, "o3": 3.0, "so2": 1.0, "nh3": 0.5},
            }
        ]
    }
    raw_record = RawAirPollutionRecord(
        raw_response_id=1,
        pipeline_run_id=1,
        city_id=1,
        city="TestCity",
        country_code="TC",
        lat=1.0,
        lon=2.0,
        geo_id="TestCity,TC:1.0000,2.0000",
        request_start_utc=datetime(2025, 1, 1, tzinfo=timezone.utc),
        request_end_utc=datetime(2025, 1, 1, tzinfo=timezone.utc),
        status_code=200,
        record_count=1,
        payload_json=payload,
        fetched_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )

    df = build_gold_from_raw_records([raw_record])
    assert len(df) == 1
    assert "risk_score" in df.columns
    assert df.loc[df.index[0], "aqi_category"] in {"Good","Fair","Moderate","Poor","Very Poor","Unknown"}
