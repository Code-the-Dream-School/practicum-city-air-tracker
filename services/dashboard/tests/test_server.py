from __future__ import annotations

import pandas as pd

from services.dashboard import server


def test_build_dashboard_payload_reads_from_postgres(monkeypatch):
    sample_df = pd.DataFrame(
        [
            {
                "ts": "2026-04-05T10:00:00+00:00",
                "city": "Lagos",
                "country_code": "NG",
                "lat": 6.4551,
                "lon": 3.3942,
                "geo_id": "Lagos,NG:6.4551,3.3942",
                "aqi": 2,
                "co": 120.1,
                "no": 0.1,
                "no2": 1.1,
                "o3": 10.2,
                "so2": 0.2,
                "nh3": 0.5,
                "pm2_5": 12.2,
                "pm10": 20.1,
                "pm2_5_24h_avg": 11.8,
                "aqi_category": "Fair",
                "risk_score": 22.4,
            },
            {
                "ts": "2026-04-05T11:00:00+00:00",
                "city": "Toronto",
                "country_code": "CA",
                "lat": 43.6535,
                "lon": -79.3839,
                "geo_id": "Toronto,CA:43.6535,-79.3839",
                "aqi": 1,
                "co": 90.4,
                "no": 0.0,
                "no2": 0.8,
                "o3": 11.0,
                "so2": 0.1,
                "nh3": 0.4,
                "pm2_5": 8.9,
                "pm10": 14.1,
                "pm2_5_24h_avg": 8.3,
                "aqi_category": "Good",
                "risk_score": 15.0,
            },
        ]
    )

    server.cache.payload = None
    server.cache.last_refresh_monotonic = None

    monkeypatch.setattr(server, "_load_dashboard_frame", lambda: sample_df)

    payload = server.build_dashboard_payload()

    assert payload["summary"]["rowCount"] == 2
    assert payload["summary"]["citiesCount"] == 2
    assert {row["geo_id"] for row in payload["latestByCity"]} == {
        "Lagos,NG:6.4551,3.3942",
        "Toronto,CA:43.6535,-79.3839",
    }
