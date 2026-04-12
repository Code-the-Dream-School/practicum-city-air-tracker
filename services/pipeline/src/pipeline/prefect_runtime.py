from __future__ import annotations

import argparse
from collections.abc import Callable
from typing import Any, TypeVar

from pipeline.common.config import settings
from pipeline.orchestration import run_pipeline_job


F = TypeVar("F", bound=Callable[..., Any])

try:
    from prefect import flow as prefect_flow

    PREFECT_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised indirectly in tests
    PREFECT_AVAILABLE = False

    def prefect_flow(*_args: Any, **_kwargs: Any) -> Callable[[F], F]:
        def decorator(func: F) -> F:
            return func

        return decorator


def _ensure_prefect_available() -> None:
    if not PREFECT_AVAILABLE:
        raise RuntimeError(
            "Prefect is not installed in the current environment. "
            "Install project dependencies before running the Prefect runtime."
        )


@prefect_flow(name="city-air-pipeline")
def run_pipeline_flow(source: str = "openweather", history_hours: int | None = None):
    """Prefect-facing flow wrapper around the shared pipeline runner."""
    _ensure_prefect_available()
    return run_pipeline_job(source=source, history_hours=history_hours)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the City Air Tracker pipeline through Prefect")
    parser.add_argument("--source", default="openweather", choices=["openweather"])
    parser.add_argument("--history-hours", type=int, default=int(settings.history_hours))
    args = parser.parse_args()

    run_pipeline_flow(source=args.source, history_hours=args.history_hours)


if __name__ == "__main__":
    main()
