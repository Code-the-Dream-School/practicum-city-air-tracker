from __future__ import annotations
from datetime import datetime, timezone

import pandas as pd

from ..extract.openweather_air_pollution import RawAirPollutionRecord
from .risk_scoring import add_risk_score, add_aqi_category


COMPONENT_KEYS = ["co", "no", "no2", "o3", "so2", "nh3", "pm2_5", "pm10"]


def build_gold_from_raw_records(raw_records: list[RawAirPollutionRecord]) -> pd.DataFrame:
    rows: list[dict] = []

    for raw_record in raw_records:
        payload = raw_record.payload_json
        city = raw_record.city
        country_code = raw_record.country_code
        lat = raw_record.lat
        lon = raw_record.lon
        geo_id = raw_record.geo_id

        for item in payload.get("list", []):
            ts = datetime.fromtimestamp(int(item["dt"]), tz=timezone.utc)
            main = item.get("main", {})
            comps = item.get("components", {})

            row = {
                "ts": ts,
                "city": city,
                "country_code": country_code,
                "lat": lat,
                "lon": lon,
                "geo_id": geo_id,
                "aqi": int(main.get("aqi")) if main.get("aqi") is not None else None,
            }
            for k in COMPONENT_KEYS:
                row[k] = float(comps[k]) if k in comps and comps[k] is not None else None
            rows.append(row)

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # basic normalization
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df = df.sort_values(["geo_id", "ts"]).drop_duplicates(["geo_id", "ts"], keep="last")

    # simple rolling feature example: pm2_5_24h_avg per geo_id
    df["pm2_5_24h_avg"] = (
        df.groupby("geo_id")["pm2_5"]
        .transform(lambda s: s.rolling(window=24, min_periods=1).mean())
    )

    df = add_aqi_category(df)
    df = add_risk_score(df)
    return df
