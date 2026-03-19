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
    storage_backend: str = "local"

    # Optional Azure-compatible storage settings used by local Docker Compose development
    azure_storage_account_name: str = "devstoreaccount1"
    azure_storage_account_key: str = (
        "Eby8vdM02xNOcqFeqCnf2FlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw=="
    )
    azure_storage_blob_endpoint: str = "http://azurite:10000/devstoreaccount1"
    azure_storage_connection_string: str = (
        "DefaultEndpointsProtocol=http;"
        "AccountName=devstoreaccount1;"
        "AccountKey=Eby8vdM02xNOcqFeqCnf2FlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
        "BlobEndpoint=http://azurite:10000/devstoreaccount1;"
    )
    azure_storage_container: str = "cityair"
    azure_storage_prefix: str = "gold"

    # Optional Postgres load
    use_postgres: bool = False
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "cityair"
    postgres_user: str = "cityair"
    postgres_password: str = "cityair"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
