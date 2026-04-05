from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # OpenWeather
    openweather_api_key: str = "7842b53c6510964cf8c2ee80d5feaab2"
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
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "cityair"
    postgres_user: str = "cityair"
    postgres_password: str = "cityair"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def postgres_sqlalchemy_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
