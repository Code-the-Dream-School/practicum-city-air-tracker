from __future__ import annotations
from pathlib import Path
import json
from datetime import datetime, timezone

from ..common.config import settings
from .http import RateLimiter, get_with_retries


# OpenWeather Air Pollution API (historical)
AIR_URL = "https://api.openweathermap.org/data/2.5/air_pollution/history"

_limiter = RateLimiter(settings.max_calls_per_minute)


def _geo_id(city: str, country_code: str, lat: float, lon: float) -> str:
    return f"{city},{country_code}:{lat:.4f},{lon:.4f}".replace(' ', '_')


def fetch_air_pollution_history(
    raw_dir: Path,
    city: str,
    country_code: str,
    lat: float,
    lon: float,
    start: datetime,
    end: datetime,
    run_id: str,
) -> Path:
    if not settings.openweather_api_key or settings.openweather_api_key == "CHANGEME":
        raise ValueError("OPENWEATHER_API_KEY must be set in .env")

    geo_id = _geo_id(city, country_code, lat, lon)
    out_dir = raw_dir / "openweather" / "air_pollution" / "history" / geo_id
    out_dir.mkdir(parents=True, exist_ok=True)

    start_ts = int(start.replace(tzinfo=timezone.utc).timestamp())
    end_ts = int(end.replace(tzinfo=timezone.utc).timestamp())

    out_path = out_dir / f"{run_id}_{start_ts}_{end_ts}.json"
    manifest_dir = raw_dir / "openweather" / "_manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / f"{run_id}_{geo_id}.json"

    # cache hit
    if out_path.exists():
        return out_path

    _limiter.wait()
    resp = get_with_retries(
        AIR_URL,
        params={
            "lat": lat,
            "lon": lon,
            "start": start_ts,
            "end": end_ts,
            "appid": settings.openweather_api_key,
        },
    )
    data = resp.json()
    out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    manifest = {
        "run_id": run_id,
        "city": city,
        "country_code": country_code,
        "lat": lat,
        "lon": lon,
        "geo_id": geo_id,
        "start_ts": start_ts,
        "end_ts": end_ts,
        "url": AIR_URL,
        "status_code": resp.status_code,
        "record_count": len(data.get("list", [])),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "raw_path": str(out_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return out_path
