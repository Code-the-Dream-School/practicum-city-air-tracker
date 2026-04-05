# City Air Tracker

This repo contains a Code the Dream-friendly batch ETL project that:

1. Geocodes global cities to lat/lon
2. Pulls OpenWeather Air Pollution historical data
3. Transforms PostgreSQL-backed raw response records into a gold dataset
4. Writes Parquet output and can optionally publish to Postgres
5. Serves a Streamlit dashboard over the gold dataset

The migration path now supports DB-first load behavior, where PostgreSQL can be the primary load target and Parquet export is an explicit setting.
City configuration, geocoding cache, and raw extract persistence are also moving into PostgreSQL as runtime state.

## Main run guide

Use `docs/setup/run_and_debug_guide.md` for:

- local Python installation
- Python library installation
- local non-Docker `.env` configuration
- local VS Code debugging
- Docker Compose installation
- Docker Compose configuration, launch, and verification

## One-command local environment setup

If you want a quick local Python setup, use the bootstrap script for your OS.

These scripts:

- create `.venv` in the project root if missing
- upgrade `pip`, `setuptools`, and `wheel`
- install dependencies from `requirements.txt`
- install the local pipeline package in editable mode for module-based execution

### WSL, Linux, or macOS

```bash
./scripts/setup_venv.sh
```

If you hit a permission error:

```bash
bash scripts/setup_venv.sh
```

### Windows PowerShell

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_venv.ps1
```

After script setup, activate the environment:

- WSL, Linux, macOS: `source .venv/bin/activate`
- Windows PowerShell: `.venv\Scripts\Activate.ps1`

Run the pipeline locally with the package entrypoint:

```bash
python -m pipeline.cli --source openweather --history-hours 72
```

This is the preferred local run path because it matches the packaged production-style entrypoint used by the pipeline service.

## PostgreSQL schema bootstrap

The PostgreSQL-first migration path uses Alembic for schema versioning.

Apply the latest schema locally with:

```bash
alembic upgrade head
```

If you are using Docker Compose, run the dedicated migration service:

```bash
docker compose run --rm migrate
```

This creates or upgrades the PostgreSQL schema before pipeline services depend on it.

## Configure cities

The pipeline now treats PostgreSQL as the runtime source of truth for cities by default.

`CITIES_FILE` remains the seed/import input used to populate the `cities` table.

Expected CSV columns:

```csv
city,country_code,state
```

Example:

```csv
Toronto,CA,
Paris,FR,
Lagos,NG,
Sydney,AU,NSW
```

Notes:

- `country_code` is required for reliable global geocoding
- `state` is optional for most countries

### Custom city files

You can point the seed/import workflow to a different city CSV by changing `CITIES_FILE`.

Examples:

```dotenv
# Local Python
CITIES_FILE=configs/cities_local.csv

# Docker Compose
CITIES_FILE=/app/configs/cities_production.csv
```

For Docker Compose, custom city files must live inside `./configs/` on the host because that directory is mounted into the containers as `/app/configs`.

### Common city-file issues

- `FileNotFoundError` during city seed/import usually means `CITIES_FILE` is misspelled or points to the wrong place
- If Docker cannot find a custom city file, make sure the file exists under `./configs/`
- If city seed/import creates no rows, confirm the CSV has at least one data row below the header
- If geocoding fails for a city, verify the `country_code`

### Seed cities into PostgreSQL

To populate the `cities` table from the configured CSV:

```bash
python -m pipeline.cli --seed-cities
```

Normal pipeline execution reads active cities from PostgreSQL when `CITIES_SOURCE=postgres`.

## Additional docs

Browse `docs/README.md` for the full categorized index.

- `docs/setup/run_and_debug_guide.md`
- `docs/setup/docker_and_compose_walkthrough.md`
- `docs/setup/github_quality_gates_setup.md`
- `docs/collaboration/github_feature_branch_pr_guide.md`
- `docs/collaboration/pr_review_best_practices.md`
- `docs/collaboration/what_is_a_data_pipeline.md`
- `docs/architecture/architecture.md`
- `docs/architecture/data_flow_diagram.md`
- `docs/architecture/postgresql_schema_design.md`
- `docs/reference/data_dictionary.md`
- `docs/reference/openweather_environmental_api_fields_reference.md`
