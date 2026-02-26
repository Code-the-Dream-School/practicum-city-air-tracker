from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
from datetime import datetime, timezone

from ..common.config import settings
from .http import RateLimiter, get_with_retries


@dataclass(frozen=True)
class Coords:
    lat: float
    lon: float


_limiter = RateLimiter(settings.max_calls_per_minute)

# OpenWeather Geocoding (direct)
GEO_URL = "https://api.openweathermap.org/geo/1.0/direct"


def _geo_cache_path(raw_dir: Path, city: str, country_code: str, state: str | None) -> Path:
    safe = f"{city}_{country_code}_{state or ''}".replace(' ', '_').replace('/', '_')
    return raw_dir / "openweather" / "geocoding" / f"{safe}.json"


def geocode_city(raw_dir: Path, city: str, country_code: str, state: str | None = None) -> Coords:
    out = _geo_cache_path(raw_dir, city, country_code, state)
    out.parent.mkdir(parents=True, exist_ok=True)

    if out.exists():
        data = json.loads(out.read_text(encoding="utf-8"))
        return Coords(lat=float(data["lat"]), lon=float(data["lon"]))

    if not settings.openweather_api_key or settings.openweather_api_key == "CHANGEME":
        raise ValueError("OPENWEATHER_API_KEY must be set in .env")

    q = f"{city},{country_code}"
    if state:
        q = f"{city},{state},{country_code}"

    _limiter.wait()
    resp = get_with_retries(
        GEO_URL,
        params={"q": q, "limit": 5, "appid": settings.openweather_api_key},
    )
    arr = resp.json()
    if not arr:
        raise ValueError(f"No geocoding results for: {q}")

    best = arr[0]  # deterministic choice for POC
    payload = {
        "query": q,
        "lat": best["lat"],
        "lon": best["lon"],
        "name": best.get("name"),
        "state": best.get("state"),
        "country": best.get("country"),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return Coords(lat=float(payload["lat"]), lon=float(payload["lon"]))
