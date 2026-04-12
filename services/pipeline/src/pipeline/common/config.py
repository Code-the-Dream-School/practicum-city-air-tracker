from urllib.parse import quote, urlencode

from pydantic_settings import BaseSettings, SettingsConfigDict


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
    azure_blob_container: str = "gold"
    azure_blob_path: str = "exports/{table_name}.parquet"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

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
