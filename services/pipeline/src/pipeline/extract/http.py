from __future__ import annotations
import time
import random
import requests
from requests import Response


class RateLimiter:
    """Simple process-wide limiter (conservative) based on 'max calls per minute'."""

    def __init__(self, max_calls_per_minute: int) -> None:
        self.interval = 60.0 / max(1, max_calls_per_minute)
        self._last = 0.0

    def wait(self) -> None:
        now = time.time()
        delta = now - self._last
        if delta < self.interval:
            time.sleep(self.interval - delta)
        self._last = time.time()


def get_with_retries(
    url: str,
    params: dict,
    headers: dict | None = None,
    timeout_s: int = 20,
    max_retries: int = 5,
) -> Response:
    backoff = 1.0
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=timeout_s)
            if resp.status_code == 429:
                # Too many requests: respect Retry-After if present, else backoff
                ra = resp.headers.get("Retry-After")
                sleep_s = float(ra) if ra and ra.isdigit() else backoff + random.uniform(0, 0.5)
                time.sleep(sleep_s)
                backoff = min(backoff * 2, 30.0)
                continue
            resp.raise_for_status()
            return resp
        except requests.RequestException:
            if attempt == max_retries:
                raise
            time.sleep(backoff + random.uniform(0, 0.5))
            backoff = min(backoff * 2, 30.0)

    raise RuntimeError("unreachable")
