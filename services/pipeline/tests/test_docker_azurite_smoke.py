import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
AZURITE_IMAGE = "mcr.microsoft.com/azure-storage/azurite"


def _compose(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", "compose", *args],
        cwd=REPO_ROOT,
        check=check,
        capture_output=True,
        text=True,
    )


def _wait_for_tcp_port(host: str, port: int, timeout_seconds: int = 30) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(1)
    return False


def _image_present(image: str) -> bool:
    result = subprocess.run(
        ["docker", "image", "inspect", image],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def test_docker_compose_azurite_smoke() -> None:
    if os.getenv("RUN_DOCKER_SMOKE_TESTS") != "1":
        pytest.skip("Set RUN_DOCKER_SMOKE_TESTS=1 to run Docker smoke tests.")

    if shutil.which("docker") is None:
        pytest.skip("Docker is not installed.")

    if not _image_present(AZURITE_IMAGE):
        subprocess.run(
            ["docker", "pull", AZURITE_IMAGE],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

    existing_container_id = _compose("ps", "-q", "azurite").stdout.strip()

    try:
        _compose("up", "-d", "azurite")

        assert _wait_for_tcp_port("127.0.0.1", 10000), (
            "Azurite did not open localhost:10000 within 30 seconds."
        )

        azurite_container_id = _compose("ps", "-q", "azurite").stdout.strip()
        assert azurite_container_id, "docker compose did not create an azurite container."

        inspect = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", azurite_container_id],
            check=True,
            capture_output=True,
            text=True,
        )
        assert inspect.stdout.strip() == "true", "Azurite container is not running."

    finally:
        if not existing_container_id:
            _compose("stop", "azurite", check=False)
            _compose("rm", "-f", "azurite", check=False)
