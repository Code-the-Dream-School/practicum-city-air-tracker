from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # OpenWeather
    openweather_api_key: str = "7842b53c6510964cf8c2ee80d5feaab2"
    history_hours: int = 72
    max_calls_per_minute: int = 50
    cities_file: str = "/app/configs/cities.csv"

    # Data paths
    data_dir: str = "/app/data"
    raw_dir: str = "/app/data/raw"
    gold_dir: str = "/app/data/gold"

    # Optional Postgres load
    use_postgres: bool = False
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "cityair"
    postgres_user: str = "cityair"
    postgres_password: str = "cityair"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
