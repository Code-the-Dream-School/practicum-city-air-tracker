from __future__ import annotations

import importlib
import sys
from pathlib import Path


def _reload_config_module():
    sys.modules.pop("pipeline.common.config", None)
    return importlib.import_module("pipeline.common.config")


def test_settings_default_to_dotenv_when_env_file_is_unset(monkeypatch):
    monkeypatch.delenv("ENV_FILE", raising=False)

    config = _reload_config_module()

    assert config._resolve_env_file() == ".env.local"
    assert config.Settings.model_config.get("env_file") == ".env.local"


def test_settings_support_custom_env_file(monkeypatch, tmp_path: Path):
    env_file = tmp_path / ".env.azure"
    env_file.write_text("POSTGRES_HOST=azure.example\n", encoding="utf-8")

    monkeypatch.setenv("ENV_FILE", str(env_file))

    config = _reload_config_module()
    settings = config.Settings()

    assert config._resolve_env_file() == str(env_file)
    assert config.Settings.model_config.get("env_file") == str(env_file)
    assert settings.postgres_host == "azure.example"
