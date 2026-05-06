import os
from urllib.parse import quote, urlencode

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _resolve_env_file() -> str:
    return os.getenv("ENV_FILE", ".env.local")


class Settings(BaseSettings):
    # OpenWeather
    openweather_api_key: str = "CHANGEME"
    history_hours: int = 72
    max_calls_per_minute: int = 50
    cities_source: str = "postgres"
    cities_file: str = "/app/configs/cities.csv"

    # Data paths
    data_dir: str = "/app/data"
    raw_dir: str = "/app/data/raw"
    gold_dir: str = "/app/data/gold"

    # PostgreSQL is the primary gold target; Parquet is optional.
    use_postgres: bool = True
    write_gold_parquet: bool = False
    write_gold_azure_blob: bool = False
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "cityair"
    postgres_user: str = "cityair"
    postgres_password: str = "cityair"
    postgres_sslmode: str = ""
    postgres_sslrootcert: str = ""
    azure_storage_connection_string: str = ""
    azure_storage_account_url: str = ""
    azure_storage_credential: str = ""
    azure_blob_container: str = "gold"
    azure_blob_path: str = "exports/{table_name}.parquet"

    # Prefect scheduling
    prefect_schedule_enabled: bool = False
    prefect_schedule_type: str | None = None
    prefect_interval_minutes: int | None = None
    prefect_cron: str | None = None
    prefect_schedule_timezone: str = "UTC"

    model_config = SettingsConfigDict(env_file=_resolve_env_file(), extra="ignore")

    @property
    def postgres_sqlalchemy_url(self) -> str:
        user = quote(self.postgres_user, safe="")
        password = quote(self.postgres_password, safe="")
        database = quote(self.postgres_db, safe="")

        query_params: dict[str, str] = {}
        if self.postgres_sslmode.strip():
            query_params["sslmode"] = self.postgres_sslmode.strip()
        if self.postgres_sslrootcert.strip():
            query_params["sslrootcert"] = self.postgres_sslrootcert.strip()

        query = f"?{urlencode(query_params)}" if query_params else ""

        return (
            f"postgresql+psycopg://{user}:{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{database}{query}"
        )

    @field_validator("prefect_schedule_type", mode="after")
    @classmethod
    def validate_schedule_type_value(cls, v, info):
        """Validate that schedule_type is one of supported types if scheduling is enabled."""
        if not info.data.get("prefect_schedule_enabled"):
            return v
        if v and v not in ("interval", "cron"):
            raise ValueError(
                f"prefect_schedule_type must be one of ['interval', 'cron'], got {v!r}"
            )
        return v

    def validate_schedule_settings(self) -> None:
        """
        Validate Prefect schedule configuration.
        
        Raises:
            ValueError: if schedule configuration is invalid
        """
        if not self.prefect_schedule_enabled:
            # If scheduling is disabled, other settings are optional
            return

        # Scheduling is enabled; validate required fields
        if not self.prefect_schedule_type:
            raise ValueError("prefect_schedule_type must be set when prefect_schedule_enabled is True")

        if self.prefect_schedule_type == "interval":
            if self.prefect_interval_minutes is None:
                raise ValueError(
                    "prefect_interval_minutes must be set when prefect_schedule_type is 'interval'"
                )
            if self.prefect_interval_minutes <= 0:
                raise ValueError(
                    f"prefect_interval_minutes must be positive, got {self.prefect_interval_minutes}"
                )

        if self.prefect_schedule_type == "cron":
            if self.prefect_cron is None:
                raise ValueError("prefect_cron must be set when prefect_schedule_type is 'cron'")
            if not self.prefect_cron.strip():
                raise ValueError("prefect_cron cannot be empty")


settings = Settings()
