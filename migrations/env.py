from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool


ROOT = Path(__file__).resolve().parents[1]
PIPELINE_SRC = ROOT / "services" / "pipeline" / "src"
if str(PIPELINE_SRC) not in sys.path:
    sys.path.insert(0, str(PIPELINE_SRC))

from pipeline.common.config import settings


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def get_database_url() -> str:
    # Allow an explicit override for migration workflows, otherwise reuse app settings.
    return os.getenv("ALEMBIC_DATABASE_URL") or settings.postgres_sqlalchemy_url


def run_migrations_offline() -> None:
    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
