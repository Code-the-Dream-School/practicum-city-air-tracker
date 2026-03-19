from __future__ import annotations

import json
import mimetypes
import os
from dataclasses import dataclass
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import pandas as pd


DEFAULT_DATA_PATH = "/app/data/gold/air_pollution_gold.parquet"
PORT = int(os.getenv("PORT", "8501"))
DATA_PATH = Path(os.getenv("DASHBOARD_DATA_PATH", DEFAULT_DATA_PATH))
STATIC_DIR = Path(__file__).resolve().parent / "static"


@dataclass
class DashboardCache:
    mtime: float | None = None
    payload: dict | None = None


cache = DashboardCache()


def _normalize_value(value):
    if pd.isna(value):
        return None

    if isinstance(value, np.generic):
        return value.item()

    if hasattr(value, "isoformat"):
        return value.isoformat()

    if isinstance(value, float):
        return round(value, 3)

    return value


def _row_to_dict(row: pd.Series) -> dict:
    return {column: _normalize_value(value) for column, value in row.items()}


def build_dashboard_payload() -> dict:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dashboard dataset not found at {DATA_PATH}")

    mtime = DATA_PATH.stat().st_mtime
    if cache.mtime == mtime and cache.payload is not None:
        return cache.payload

    df = pd.read_parquet(DATA_PATH)
    if df.empty:
        payload = {
            "rows": [],
            "latestByCity": [],
            "summary": {
                "rowCount": 0,
                "citiesCount": 0,
                "latestTimestamp": None,
                "averageAqi": None,
                "highestRiskCity": None,
                "worstPm25City": None,
            },
        }
    else:
        df = df.copy()
        df["ts"] = pd.to_datetime(df["ts"], utc=True)
        df = df.sort_values(["geo_id", "ts"])
        latest_by_city = df.groupby("geo_id", as_index=False).tail(1).sort_values(["city", "country_code"])

        payload = {
            "rows": [_row_to_dict(row) for _, row in df.iterrows()],
            "latestByCity": [_row_to_dict(row) for _, row in latest_by_city.iterrows()],
            "summary": {
                "rowCount": int(len(df)),
                "citiesCount": int(latest_by_city["geo_id"].nunique()),
                "latestTimestamp": _normalize_value(df["ts"].max()),
                "averageAqi": float(latest_by_city["aqi"].mean()) if latest_by_city["aqi"].notna().any() else None,
                "highestRiskCity": _row_to_dict(
                    latest_by_city.sort_values("risk_score", ascending=False).iloc[0]
                ),
                "worstPm25City": _row_to_dict(latest_by_city.sort_values("pm2_5", ascending=False).iloc[0]),
            },
        }

    cache.mtime = mtime
    cache.payload = payload
    return payload


class DashboardRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._send_json({"status": "ok"})
            return

        if parsed.path == "/api/dashboard":
            try:
                payload = build_dashboard_payload()
            except FileNotFoundError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.NOT_FOUND)
                return
            except Exception as exc:  # pragma: no cover - defensive HTTP fallback
                self._send_json({"error": f"Dashboard API failed: {exc}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return

            self._send_json(payload)
            return

        candidate = STATIC_DIR / parsed.path.lstrip("/")
        if parsed.path != "/" and candidate.exists() and candidate.is_file():
            return super().do_GET()

        self.path = "/index.html"
        return super().do_GET()

    def log_message(self, format: str, *args) -> None:  # noqa: A003 - stdlib signature
        print(f"[dashboard] {self.address_string()} - {format % args}")

    def guess_type(self, path: str) -> str:
        if path.endswith(".js"):
            return "text/javascript"
        return mimetypes.guess_type(path)[0] or "application/octet-stream"

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    if not STATIC_DIR.exists():
        raise FileNotFoundError(
            f"Static dashboard assets not found at {STATIC_DIR}. Build the React frontend before starting the server."
        )

    server = ThreadingHTTPServer(("0.0.0.0", PORT), DashboardRequestHandler)
    print(f"City Air Tracker dashboard listening on http://0.0.0.0:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
