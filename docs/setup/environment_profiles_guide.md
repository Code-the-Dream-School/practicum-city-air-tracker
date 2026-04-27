# Environment Profiles Guide

This guide shows how to keep separate local and Azure environment settings
without overwriting your normal Docker Compose development configuration.

## Recommended layout

Keep these files at the repository root:

- `.env.local`
  for the normal local Docker and local PostgreSQL workflow
- `.env.azure`
  for real Azure PostgreSQL and other cloud-only values
- `configs/env/local.template`
  tracked local starter template
- `configs/env/azure.template`
  tracked Azure starter template

Only the tracked templates under `configs/env/` should be committed.

## Create the Azure profile

Generate both local and Azure profiles from the tracked templates:

```bash
bash scripts/generate_env_profiles.sh
```

This creates:

- `.env.local` from `configs/env/local.template`
- `.env.azure` from `configs/env/azure.template`

Then replace the placeholders in `.env.azure` with your real Azure values.

Example Azure PostgreSQL block:

```dotenv
USE_POSTGRES=1
POSTGRES_HOST=YOUR_SERVER.postgres.database.azure.com
POSTGRES_PORT=5432
POSTGRES_DB=postgres
POSTGRES_USER=YOUR_USER@YOUR_SERVER
POSTGRES_PASSWORD=YOUR_PASSWORD
POSTGRES_SSLMODE=require
POSTGRES_SSLROOTCERT=
```

## Which file is active

The application settings loader reads the file named by `ENV_FILE`.

- if `ENV_FILE` is unset, the default is `.env.local`
- if `ENV_FILE=.env.azure`, the Azure profile becomes active

That means you can keep both files side by side without copying one over the
other.

## Supported run modes

The env-profile workflow supports these run modes:

1. Local without Docker
   Run Python and Alembic directly on your machine, usually with `.env.local`
   edited to use local filesystem paths and `POSTGRES_HOST=localhost`.
2. Local with Docker
   Run `docker compose up --build` with `.env.local` using the Docker-oriented
   defaults from `configs/env/local.template`.
3. Cloud-connected
   Run local Python commands, Alembic commands, or Docker Compose with
   `ENV_FILE=.env.azure` so the app uses Azure-backed services.

Important:

- the cloud-connected mode means the app runs locally or in local containers
  while talking to cloud resources
- it is not the same as deploying the app itself to Azure

## Run with the Azure profile

For local Python commands, prefix the command with `ENV_FILE=.env.azure`:

```bash
ENV_FILE=.env.azure python -m pipeline.cli --source openweather --history-hours 72
```

For Alembic commands:

```bash
ENV_FILE=.env.azure alembic current
ENV_FILE=.env.azure alembic upgrade head
```

For Docker Compose:

```bash
ENV_FILE=.env.azure docker compose up --build
```

## Keep both profiles safely

An easy workflow is:

1. keep your local Docker settings in `.env.local`
2. keep your Azure settings in `.env.azure`
3. run commands with `ENV_FILE=.env.azure` only when you want the cloud profile

## Alembic migrations

Alembic uses the same shared settings path, so `ENV_FILE=.env.azure` switches
the migration target to the Azure profile too.

You can also set `ALEMBIC_DATABASE_URL` explicitly in `.env.azure` if you want
the migration target to be fully explicit.

## Security notes

- never commit `.env.local` or `.env.azure`
- commit only the tracked templates under `configs/env/`
- prefer secret stores or deployment environment variables for shared or
  production environments

For Azure-specific PostgreSQL details, use
[azure_postgresql_configuration.md](/home/eugen/code-the-dream-workspace/practicum-city-air-tracker/docs/setup/azure_postgresql_configuration.md).
