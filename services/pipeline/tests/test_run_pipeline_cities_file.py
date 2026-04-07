from argparse import Namespace
from pathlib import Path
import pytest

import pipeline.cli as pipeline_cli
import run_pipeline


def test_main_routes_cli_arguments_through_shared_runner(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        pipeline_cli.argparse.ArgumentParser,
        "parse_args",
        lambda self: Namespace(source="openweather", history_hours=72, seed_cities=False),
    )

    captured: dict[str, object] = {}

    def fake_run_pipeline_job(*, source: str, history_hours: int):
        captured["source"] = source
        captured["history_hours"] = history_hours

    monkeypatch.setattr(pipeline_cli, "run_pipeline_job", fake_run_pipeline_job)

    run_pipeline.main()

    assert captured == {"source": "openweather", "history_hours": 72}


def test_main_propagates_runner_failures(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        pipeline_cli.argparse.ArgumentParser,
        "parse_args",
        lambda self: Namespace(source="openweather", history_hours=72, seed_cities=False),
    )

    def fake_run_pipeline_job(*, source: str, history_hours: int):
        raise FileNotFoundError("CITIES_FILE path does not exist: missing-cities.csv")

    monkeypatch.setattr(pipeline_cli, "run_pipeline_job", fake_run_pipeline_job)

    with pytest.raises(FileNotFoundError, match=r"CITIES_FILE path does not exist"):
        run_pipeline.main()


def test_main_supports_seed_cities(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        pipeline_cli.argparse.ArgumentParser,
        "parse_args",
        lambda self: Namespace(source="openweather", history_hours=72, seed_cities=True),
    )

    captured: dict[str, object] = {}

    monkeypatch.setattr(
        pipeline_cli,
        "seed_cities_from_file",
        lambda path: captured.setdefault("cities_file", path),
    )
    monkeypatch.setattr(
        pipeline_cli,
        "run_pipeline_job",
        lambda **kwargs: captured.setdefault("ran_pipeline", kwargs),
    )

    run_pipeline.main()

    assert captured == {"cities_file": Path(pipeline_cli.settings.cities_file)}
