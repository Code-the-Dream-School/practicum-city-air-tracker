# Docker And Compose Walkthrough

This guide explains the Docker-related files in the repository using the current implementation.

It focuses on:

- `services/pipeline/Dockerfile`
- `services/dashboard/Dockerfile`
- `docker-compose.yml`

It also explains how the local Azure-compatible Blob flow works through Azurite and the browser-based storage explorer.

## `services/pipeline/Dockerfile`

Current file:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY pyproject.toml /app/pyproject.toml
COPY alembic.ini /app/alembic.ini
COPY migrations /app/migrations
COPY services/pipeline /app/services/pipeline
COPY configs /app/configs
RUN pip install --no-cache-dir --no-build-isolation --no-deps /app

ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "pipeline.cli", "--source", "openweather", "--history-hours", "72"]
```

What this image does:

- starts from Python 3.11 slim
- installs build tools needed by some Python dependencies
- installs Python dependencies from `requirements.txt`
- copies `pyproject.toml`, Alembic config, migrations, pipeline code, and config files into the image
- installs the local pipeline package so module-based execution works inside the container
- runs the pipeline through `python -m pipeline.cli`, which matches the current packaged entrypoint

Important details:

- `COPY services/pipeline /app/services/pipeline` preserves the package layout expected by `pyproject.toml`
- `COPY alembic.ini` and `COPY migrations` make the same image usable for the `migrate` service
- `PYTHONUNBUFFERED=1` keeps container logs visible immediately in `docker compose logs`

## `services/dashboard/Dockerfile`

The dashboard build is a multi-stage image:

- a Node/Vite build stage compiles the frontend assets
- a Python runtime stage serves the API and static frontend

The dashboard container serves the app on port `8501`.

## `docker-compose.yml`

The local stack now contains seven services:

- `postgres`
- `migrate`
- `pipeline`
- `dashboard`
- `adminer`
- `azurite`
- `azurestorageexplorer`

### Startup model

The compose file uses dependency conditions so startup is more reliable:

- `postgres` has a healthcheck
- `migrate` waits until PostgreSQL is healthy
- `pipeline` waits for:
  - healthy PostgreSQL
  - successful migrations
  - started Azurite
- `dashboard` and `adminer` also wait for healthy PostgreSQL

This avoids the earlier race where the pipeline could start before the database schema was ready.

## Service-by-service explanation

### `postgres`

- local PostgreSQL database
- stores:
  - `cities`
  - `geocoding_cache`
  - `pipeline_runs`
  - `raw_air_pollution_responses`
  - `air_pollution_gold`
- exposed on `localhost:5432`
- uses a named volume so DB state survives container restarts

### `migrate`

- runs `alembic upgrade head`
- prepares the PostgreSQL schema before the pipeline runs
- uses the same pipeline image because that image now includes Alembic config and migrations
- exits after the migration completes

### `pipeline`

- runs the ETL batch job as a one-shot container
- uses:

```yaml
command: ["python", "-m", "pipeline.cli", "--source", "openweather", "--history-hours", "72"]
```

- mounts:
  - `./data:/app/data`
  - `./configs:/app/configs:ro`
- reads settings from `.env`
- depends on healthy PostgreSQL, successful migrations, and started Azurite

### `dashboard`

- runs the dashboard server on port `8501`
- reads PostgreSQL-backed data
- uses environment variables from `.env`, with Compose defaults for common local DB settings

### `adminer`

- lightweight browser UI for PostgreSQL
- exposed on `http://localhost:8080`
- useful for inspecting tables and query results manually

### `azurite`

- local Azure Blob emulator
- exposed on `http://localhost:10000`
- used when `WRITE_GOLD_AZURE_BLOB=1`
- stores emulator data in a named Docker volume
- starts with `--skipApiVersionCheck` to stay compatible with the current Azure SDK behavior in local development

### `azurestorageexplorer`

- browser-based storage explorer for Azurite
- exposed on `http://localhost:8081`
- preconfigured with:
  - `AZURITE=true`
  - `AZURE_STORAGE_CONNECTIONSTRING=${AZURE_STORAGE_CONNECTION_STRING}`
- used to verify that the gold Parquet artifact was uploaded successfully

## How the local Azure-compatible Blob flow works

When these settings are enabled:

```dotenv
USE_POSTGRES=1
WRITE_GOLD_PARQUET=0
WRITE_GOLD_AZURE_BLOB=1
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=...;BlobEndpoint=http://azurite:10000/devstoreaccount1;
AZURE_BLOB_CONTAINER=gold
AZURE_BLOB_PATH=exports/{table_name}.parquet
```

the pipeline will:

1. upsert the gold dataset into PostgreSQL
2. create the `gold` blob container if it does not already exist
3. upload the Parquet artifact to:

```text
exports/air_pollution_gold.parquet
```

inside the `gold` container

You can then verify the upload in the browser explorer at `http://localhost:8081`.

Expected blob location:

- container: `gold`
- path: `exports/air_pollution_gold.parquet`

Important UI note:

- inside the browser explorer, the path should be `exports/`

This Docker Compose flow is for local Azurite development. To publish the same
artifact to real Azure Blob Storage, keep the same environment variable names
and replace the Azurite connection string with your production Azure connection
string. See [`azure_blob_storage_configuration.md`](./azure_blob_storage_configuration.md).
- not `gold/exports/`

## Recommended commands

Clean start:

```bash
docker compose down -v
docker compose up --build
```

Run only migrations:

```bash
docker compose run --rm migrate
```

Run only the pipeline:

```bash
docker compose run --rm pipeline python -m pipeline.cli --source openweather --history-hours 72
```

Check container state:

```bash
docker compose ps
```

Check pipeline logs:

```bash
docker compose logs pipeline
```

Check Azurite logs:

```bash
docker compose logs azurite
```

## Summary

The Compose stack now supports the full local workflow:

- PostgreSQL-first pipeline execution
- schema bootstrap through Alembic
- local dashboard access
- local PostgreSQL inspection through Adminer
- Azure-compatible Blob upload testing through Azurite
- browser-based Blob verification through Azure Storage Web Explorer
