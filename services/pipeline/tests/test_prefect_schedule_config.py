from __future__ import annotations

import pytest

from pipeline.common.config import Settings


def test_default_schedule_is_disabled():
    """Default schedule configuration should be safe for local development."""
    settings = Settings()

    assert settings.prefect_schedule_enabled is False
    assert settings.prefect_schedule_type is None
    assert settings.prefect_interval_minutes is None
    assert settings.prefect_cron is None
    assert settings.prefect_schedule_timezone == "UTC"


def test_validate_schedule_settings_passes_when_scheduling_disabled():
    """Validation should pass when scheduling is disabled, regardless of other fields."""
    settings = Settings(
        prefect_schedule_enabled=False,
        prefect_schedule_type=None,
        prefect_interval_minutes=None,
        prefect_cron=None,
    )

    # Should not raise
    settings.validate_schedule_settings()


def test_validate_schedule_settings_requires_schedule_type_when_enabled():
    """If scheduling is enabled, schedule_type must be set."""
    settings = Settings(
        prefect_schedule_enabled=True,
        prefect_schedule_type=None,
    )

    with pytest.raises(ValueError, match="prefect_schedule_type must be set"):
        settings.validate_schedule_settings()


def test_validate_schedule_settings_requires_interval_minutes_for_interval_type():
    """If schedule_type is 'interval', interval_minutes must be set."""
    settings = Settings(
        prefect_schedule_enabled=True,
        prefect_schedule_type="interval",
        prefect_interval_minutes=None,
    )

    with pytest.raises(ValueError, match="prefect_interval_minutes must be set"):
        settings.validate_schedule_settings()


def test_validate_schedule_settings_interval_minutes_must_be_positive():
    """interval_minutes must be a positive number."""
    settings = Settings(
        prefect_schedule_enabled=True,
        prefect_schedule_type="interval",
        prefect_interval_minutes=0,
    )

    with pytest.raises(ValueError, match="prefect_interval_minutes must be positive"):
        settings.validate_schedule_settings()

    settings = Settings(
        prefect_schedule_enabled=True,
        prefect_schedule_type="interval",
        prefect_interval_minutes=-1,
    )

    with pytest.raises(ValueError, match="prefect_interval_minutes must be positive"):
        settings.validate_schedule_settings()


def test_validate_schedule_settings_requires_cron_for_cron_type():
    """If schedule_type is 'cron', cron must be set."""
    settings = Settings(
        prefect_schedule_enabled=True,
        prefect_schedule_type="cron",
        prefect_cron=None,
    )

    with pytest.raises(ValueError, match="prefect_cron must be set"):
        settings.validate_schedule_settings()


def test_validate_schedule_settings_cron_cannot_be_empty():
    """Cron expression cannot be empty or whitespace."""
    settings = Settings(
        prefect_schedule_enabled=True,
        prefect_schedule_type="cron",
        prefect_cron="   ",
    )

    with pytest.raises(ValueError, match="prefect_cron cannot be empty"):
        settings.validate_schedule_settings()


def test_validate_schedule_type_rejects_unsupported_type():
    """Only 'interval' and 'cron' are supported schedule types."""
    with pytest.raises(ValueError, match="prefect_schedule_type must be one of"):
        Settings(
            prefect_schedule_enabled=True,
            prefect_schedule_type="invalid",
        )


def test_valid_interval_schedule_configuration():
    """Valid interval schedule should parse without error."""
    settings = Settings(
        prefect_schedule_enabled=True,
        prefect_schedule_type="interval",
        prefect_interval_minutes=60,
        prefect_schedule_timezone="America/New_York",
    )

    # Should not raise
    settings.validate_schedule_settings()


def test_valid_cron_schedule_configuration():
    """Valid cron schedule should parse without error."""
    settings = Settings(
        prefect_schedule_enabled=True,
        prefect_schedule_type="cron",
        prefect_cron="0 2 * * *",
        prefect_schedule_timezone="UTC",
    )

    # Should not raise
    settings.validate_schedule_settings()


def test_schedule_timezone_has_sensible_default():
    """Schedule timezone should default to UTC."""
    settings = Settings()

    assert settings.prefect_schedule_timezone == "UTC"


def test_schedule_type_none_is_valid_when_scheduling_disabled():
    """schedule_type=None should be acceptable when scheduling is disabled."""
    settings = Settings(
        prefect_schedule_enabled=False,
        prefect_schedule_type=None,
    )

    # Should not raise
    settings.validate_schedule_settings()
