# Local PostgreSQL-First Workflow

This guide documents the normal local development path for the current PostgreSQL-first pipeline.

Use this workflow when you want to:

- run the ETL pipeline locally
- bootstrap the schema from scratch
- seed cities into PostgreSQL
- verify raw and gold data in the database
- run the DB-native test suite

## Prerequisites

Before you start, make sure you have:

- Python `3.11+`
- a local PostgreSQL instance
- an OpenWeather API key
- a virtual environment with the repo dependencies installed

If you have not set up Python yet, start with [run_and_debug_guide.md](/home/eugen/code-the-dream-workspace/practicum-city-air-tracker/docs/setup/run_and_debug_guide.md).

## 1. Configure `.env`

Create `.env` from `.env.example`, then use local machine paths and PostgreSQL settings like these:

```dotenv
OPENWEATHER_API_KEY=YOUR_REAL_KEY
HISTORY_HOURS=72
MAX_CALLS_PER_MINUTE=50
CITIES_SOURCE=postgres
CITIES_FILE=configs/cities.csv

DATA_DIR=./data
RAW_DIR=./data/raw
GOLD_DIR=./data/gold

USE_POSTGRES=1
WRITE_GOLD_PARQUET=0
WRITE_GOLD_AZURE_BLOB=0
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=cityair
POSTGRES_USER=cityair
POSTGRES_PASSWORD=cityair
AZURE_STORAGE_CONNECTION_STRING=
AZURE_BLOB_CONTAINER=gold
AZURE_BLOB_PATH=exports/{table_name}.parquet

```

Notes:

- `USE_POSTGRES=1` keeps PostgreSQL as the primary gold-data target.
- `WRITE_GOLD_PARQUET=0` disables Parquet unless you explicitly want a secondary export for debugging or compatibility.
- `WRITE_GOLD_AZURE_BLOB=0` keeps Azure Blob publishing disabled during normal local DB-first work unless you are explicitly testing the Blob path.
- when you do enable Blob publishing, you can target either local Azurite or real Azure Blob Storage by changing only the Azure environment variables; see [azure_blob_storage_configuration.md](./azure_blob_storage_configuration.md)
- `CITIES_SOURCE=postgres` means normal pipeline runs read cities from the database.
- `CITIES_FILE` is still used for the seed/import step.

## 2. Bootstrap the schema

Apply the latest schema with Alembic:

```bash
alembic upgrade head
```

Verify the tables exist:

```bash
psql postgresql://cityair:cityair@localhost:5432/cityair -c "\dt"
```

Expected tables include:

- `cities`
- `geocoding_cache`
- `pipeline_runs`
- `raw_air_pollution_responses`
- `air_pollution_gold`

## 3. Seed cities

Populate the `cities` table from the configured CSV:

```bash
python -m pipeline.cli --seed-cities
```

Verify the seed worked:

```bash
psql postgresql://cityair:cityair@localhost:5432/cityair -c "select id, city, country_code, state from cities order by id;"
```

## 4. Run the pipeline

Run the ETL pipeline:

```bash
python -m pipeline.cli --source openweather --history-hours 72
```

This is the preferred local entrypoint because it matches the packaged pipeline module path.

## 5. Verify the database results

Check that the run was recorded:

```bash
psql postgresql://cityair:cityair@localhost:5432/cityair -c "select id, run_id, status, city_count, raw_response_count, gold_row_count from pipeline_runs order by id desc limit 5;"
```

Check that raw responses were stored:

```bash
psql postgresql://cityair:cityair@localhost:5432/cityair -c "select count(*) from raw_air_pollution_responses;"
```

Check that gold data was stored:

```bash
psql postgresql://cityair:cityair@localhost:5432/cityair -c "select count(*) from air_pollution_gold;"
```

Optional checks:

- inspect `geocoding_cache` to confirm cached coordinates were stored
- enable `WRITE_GOLD_PARQUET=1` only if you intentionally want a secondary Parquet export
- enable `WRITE_GOLD_AZURE_BLOB=1` only if you intentionally want to test Blob publishing

## 6. Run DB-native tests

Run the focused DB-native integration suite:

```bash
pytest services/pipeline/tests/test_db_native_pipeline_integration.py
```

Run a slightly broader PostgreSQL-first regression set:

```bash
pytest services/pipeline/tests/test_postgres_config.py \
  services/pipeline/tests/test_storage_publish.py \
  services/pipeline/tests/test_orchestration_runner.py \
  services/pipeline/tests/test_db_native_pipeline_integration.py
```

## 7. Debug locally in VS Code

For local debugging:

- keep the same PostgreSQL-first `.env` settings
- use local paths such as `./data/raw` and `./data/gold`
- keep `USE_POSTGRES=1`
- leave `WRITE_GOLD_PARQUET=0` unless you need a file artifact for dashboard debugging
- leave `WRITE_GOLD_AZURE_BLOB=0` unless you are testing the Azurite or Azure upload path

The current dashboard still reads Parquet, so dashboard debugging is a temporary exception to the DB-first runtime path.
The React dashboard runs from `services/dashboard/server.py` and reads PostgreSQL-backed data through `/api/dashboard`.

## Current limitations

- PostgreSQL is the primary runtime store for the pipeline.
- The dashboard API and frontend depend on the dashboard server and built React assets.
- Parquet is a secondary compatibility artifact, not the primary gold-data contract.
