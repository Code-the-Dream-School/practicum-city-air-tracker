from pipeline.common.config import Settings


def test_default_gold_target_is_postgres_first():
    settings = Settings()

    assert settings.use_postgres is True
    assert settings.write_gold_parquet is False


def test_postgres_sqlalchemy_url_uses_postgres_settings():
    settings = Settings(
        postgres_host="db.example",
        postgres_port=6543,
        postgres_db="analytics",
        postgres_user="cityair",
        postgres_password="secret",
    )

    assert settings.postgres_sqlalchemy_url == (
        "postgresql+psycopg://cityair:secret@db.example:6543/analytics"
    )


def test_postgres_sqlalchemy_url_supports_ssl_query_settings():
    settings = Settings(
        postgres_host="server.postgres.database.azure.com",
        postgres_port=5432,
        postgres_db="analytics",
        postgres_user="cityair@server",
        postgres_password="secret",
        postgres_sslmode="require",
        postgres_sslrootcert="/etc/ssl/certs/azure-ca.pem",
    )

    assert settings.postgres_sqlalchemy_url == (
        "postgresql+psycopg://cityair%40server:secret"
        "@server.postgres.database.azure.com:5432/analytics"
        "?sslmode=require&sslrootcert=%2Fetc%2Fssl%2Fcerts%2Fazure-ca.pem"
    )


def test_postgres_sqlalchemy_url_urlencodes_special_characters():
    settings = Settings(
        postgres_host="db.example",
        postgres_port=5432,
        postgres_db="city air",
        postgres_user="cityair@server",
        postgres_password="p@ss word:/!",
    )

    assert settings.postgres_sqlalchemy_url == (
        "postgresql+psycopg://cityair%40server:p%40ss%20word%3A%2F%21@db.example:5432/city%20air"
    )
