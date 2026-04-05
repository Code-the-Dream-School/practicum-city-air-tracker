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
