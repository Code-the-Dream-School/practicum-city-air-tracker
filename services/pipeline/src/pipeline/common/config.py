import os
from pathlib import Path
from urllib.parse import quote, urlencode

from pydantic_settings import BaseSettings, SettingsConfigDict


def _resolve_env_file() -> str:
    return os.getenv("ENV_FILE", ".env.local")


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


def _using_container_runtime() -> bool:
    return Path("/app").exists() and Path.cwd().as_posix().startswith("/app")


def _host_localize_app_path(value: str) -> str:
    if not value.startswith("/app/") or _using_container_runtime():
        return value

    relative_path = Path(value).relative_to("/app")
    return str(_repo_root() / relative_path)


def _host_localize_postgres_host(value: str) -> str:
    if value != "postgres" or _using_container_runtime():
        return value
    return "localhost"


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

    model_config = SettingsConfigDict(env_file=_resolve_env_file(), extra="ignore")

    def model_post_init(self, __context) -> None:
        object.__setattr__(self, "cities_file", _host_localize_app_path(self.cities_file))
        object.__setattr__(self, "data_dir", _host_localize_app_path(self.data_dir))
        object.__setattr__(self, "raw_dir", _host_localize_app_path(self.raw_dir))
        object.__setattr__(self, "gold_dir", _host_localize_app_path(self.gold_dir))
        object.__setattr__(self, "postgres_host", _host_localize_postgres_host(self.postgres_host))

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


settings = Settings()
