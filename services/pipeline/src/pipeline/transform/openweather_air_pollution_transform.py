from __future__ import annotations
from pathlib import Path
import json
from datetime import datetime, timezone
import pandas as pd

from .risk_scoring import add_risk_score, add_aqi_category


COMPONENT_KEYS = ["co", "no", "no2", "o3", "so2", "nh3", "pm2_5", "pm10"]


def _infer_city_meta(path: Path) -> tuple[str, str, float, float, str]:
    # path: .../history/<geo_id>/<file>.json
    geo_id = path.parent.name
    # geo_id: City,CC:lat,lon
    head, coords = geo_id.split(":")
    city_cc = head.split(",")
    city = city_cc[0].replace("_", " ")
    country_code = city_cc[1]
    lat_s, lon_s = coords.split(",")
    return city, country_code, float(lat_s), float(lon_s), geo_id


def build_gold_from_raw(raw_files: list[Path]) -> pd.DataFrame:
    rows: list[dict] = []

    for p in raw_files:
        payload = json.loads(p.read_text(encoding="utf-8"))
        city, country_code, lat, lon, geo_id = _infer_city_meta(p)

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
