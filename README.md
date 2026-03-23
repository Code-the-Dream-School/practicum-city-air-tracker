# City Air Tracker

This repo contains a Code the Dream-friendly batch ETL project that:

1. Geocodes global cities to lat/lon
2. Pulls OpenWeather Air Pollution historical data
3. Transforms raw JSON into a gold dataset
4. Writes Parquet output and can optionally publish to Postgres
5. Serves a Streamlit dashboard over the gold dataset

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

## Configure cities

The pipeline reads target cities from `CITIES_FILE`.

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

You can point the pipeline to a different city CSV by changing `CITIES_FILE`.

Examples:

```dotenv
# Local Python
CITIES_FILE=configs/cities_local.csv

# Docker Compose
CITIES_FILE=/app/configs/cities_production.csv
```

For Docker Compose, custom city files must live inside `./configs/` on the host because that directory is mounted into the containers as `/app/configs`.

### Common city-file issues

- `FileNotFoundError` on startup usually means `CITIES_FILE` is misspelled or points to the wrong place
- If Docker cannot find a custom city file, make sure the file exists under `./configs/`
- If the pipeline produces no output, confirm the CSV has at least one data row below the header
- If geocoding fails for a city, verify the `country_code`

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
- `docs/reference/data_dictionary.md`
- `docs/reference/openweather_environmental_api_fields_reference.md`
