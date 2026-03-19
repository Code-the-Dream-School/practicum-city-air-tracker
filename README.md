# City Air Tracker — OpenWeather (72h History) Data Pipeline

This repo is a Code the Dream-friendly scaffold for a batch ETL data pipeline that:
1. Geocodes global cities to lat/lon
2. Pulls OpenWeather Air Pollution (Historical) data for the last 72 hours
3. Transforms raw JSON into a tidy gold dataset
4. Loads to Parquet (and optionally Postgres)
5. Serves a Streamlit dashboard that reads the gold dataset

## Prerequisites

- Python 3.11+ (3.12 is currently used in this workspace)
- OpenWeather API key
- Optional: Docker + Docker Compose

## Setup Choice

Use one of these options:
- Local Python + `venv` (recommended for day-to-day development)
- Docker Compose (recommended if you want a consistent containerized environment)

`requirements.txt` defines dependencies, while `venv` isolates them per project so different machines and projects do not conflict.

## One-Command Local Setup (Recommended)

Use the project bootstrap script for your OS. The scripts:
- create `.venv` in the project root (if missing)
- upgrade `pip`, `setuptools`, `wheel`
- install dependencies from `requirements.txt`

Run from the project root:

```bash
cd /path/to/practicum-city-air-tracker
```

- WSL/macOS/Linux:

```bash
./scripts/setup_venv.sh
```

If you see a permission error, run:

```bash
bash scripts/setup_venv.sh
```

- Windows PowerShell (no WSL):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_venv.ps1
```

After script setup, activate the environment:
- WSL/macOS/Linux: `source .venv/bin/activate`
- Windows PowerShell: `.venv\Scripts\Activate.ps1`

You can rerun either script any time to refresh dependencies after changes to `requirements.txt`.

Then create your env file:

```bash
cp .env.example .env
# On Windows PowerShell use: Copy-Item .env.example .env
# Edit .env and set OPENWEATHER_API_KEY
```

## Local Setup: Windows + WSL 

Run from the WSL shell in the project folder:

```bash
cd ~/code-the-dream-workspace/practicum-city-air-tracker

# Optional if you use pyenv
pyenv local 3.12.2

python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt

cp .env.example .env
# Edit .env and set OPENWEATHER_API_KEY
```

Run pipeline and dashboard:

```bash
python services/pipeline/run_pipeline.py --source openweather --history-hours 72
streamlit run services/dashboard/app/Home.py
```

## Local Setup: Windows (no WSL)

Use PowerShell from the project root:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt

Copy-Item .env.example .env
# Edit .env and set OPENWEATHER_API_KEY
```

If PowerShell blocks activation scripts, run once as admin:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Run pipeline and dashboard:

```powershell
python services/pipeline/run_pipeline.py --source openweather --history-hours 72
streamlit run services/dashboard/app/Home.py
```

## Local Setup: macOS

From the project root:

```bash
# Optional if you use pyenv
pyenv local 3.12.2

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt

cp .env.example .env
# Edit .env and set OPENWEATHER_API_KEY
```

Run pipeline and dashboard:

```bash
python services/pipeline/run_pipeline.py --source openweather --history-hours 72
streamlit run services/dashboard/app/Home.py
```

## Docker Setup (Optional)

Use this if you want to avoid local Python setup differences across OSes.

```bash
cp .env.example .env
# Set OPENWEATHER_API_KEY in .env

docker compose up --build
```

Outputs:
- Dashboard: http://localhost:8501
- Gold output: `data/gold/air_pollution_gold.parquet`
- Raw cache: `data/raw/openweather/...`
- Azurite blob endpoint: `http://localhost:10000/devstoreaccount1`

Stop services:

```bash
docker compose down
```

Docker note: you do not need your host `.venv` when running with Docker Compose. Each container installs Python dependencies inside the image (see `services/pipeline/Dockerfile` and `services/dashboard/Dockerfile`).

## Docker Compose Azure Local Dev

Docker Compose now includes an `azurite` service so contributors can run an Azure-compatible blob emulator locally.

The default Compose behavior still keeps `STORAGE_BACKEND=local`, so the current pipeline continues writing the gold dataset to `data/gold/air_pollution_gold.parquet`. The Azure-related environment variables are included so local development can use the same emulator-friendly settings that future Azure-backed storage changes will expect.

Typical flow:

```bash
cp .env.example .env
# Set OPENWEATHER_API_KEY in .env

docker compose up --build
```

Important local development settings:
- `AZURE_STORAGE_ACCOUNT_NAME=devstoreaccount1`
- `AZURE_STORAGE_BLOB_ENDPOINT=http://azurite:10000/devstoreaccount1`
- `AZURE_STORAGE_CONNECTION_STRING=...BlobEndpoint=http://azurite:10000/devstoreaccount1;`
- `AZURE_STORAGE_CONTAINER=cityair`
- `AZURE_STORAGE_PREFIX=gold`

Use the bundled Azurite defaults only for local development. They should not be reused for real Azure deployments.

To verify that Azurite is available and starts correctly in Docker, run:

```bash
RUN_DOCKER_SMOKE_TESTS=1 pytest services/pipeline/tests/test_docker_azurite_smoke.py -q
```

The smoke test will pull the Azurite image if needed, start the `azurite` service, and verify that `localhost:10000` is reachable.

More detail is in `docs/docker_compose_azure_local_dev.md`.

## Verify The Stack

After `docker compose up --build`, use this checklist to confirm the full stack is working:

1. Check service status:

```bash
docker compose ps
```

Expected:
- `dashboard`, `postgres`, `adminer`, and `azurite` should be running.
- `pipeline` may exit after it finishes, which is normal for this batch job.

2. Check pipeline logs:

```bash
docker compose logs pipeline
```

Expected:
- the pipeline starts
- cities are processed
- the run ends with a successful completion message

3. Confirm the gold dataset exists:

```bash
ls data/gold
```

Expected:
- `air_pollution_gold.parquet`

4. Open the dashboard:

- `http://localhost:8501`

Expected:
- the dashboard loads and shows metrics and tables instead of a "Gold dataset not found" warning

5. Optional endpoint checks:

- Adminer: `http://localhost:8080`
- Azurite blob endpoint: `http://localhost:10000/devstoreaccount1`

If something fails, start with:

```bash
docker compose logs
```

Or inspect one service at a time:

```bash
docker compose logs dashboard
docker compose logs postgres
docker compose logs azurite
```

## Daily Use

Activate environment first:
- WSL/macOS: `source .venv/bin/activate`
- Windows PowerShell: `.venv\Scripts\Activate.ps1`

Then run:

```bash
python services/pipeline/run_pipeline.py --source openweather --history-hours 72
streamlit run services/dashboard/app/Home.py
```

Deactivate when done:

```bash
deactivate
```

## Configure Cities

Edit `configs/cities.csv`:

```csv
city,country_code,state
Toronto,CA,
Paris,FR,
Lagos,NG,
Sydney,AU,NSW
```

For global cities, `country_code` is required to disambiguate.

## Notes for Team Collaboration

- `.venv` is local and should not be committed.
- One teammate can use `venv` while another uses global Python; code and commands stay the same once Python dependencies are installed.
- Prefer `python -m pip ...` for cross-platform consistency.

## Docs / Diagrams

- `docs/architecture.md` - component + sequence diagrams (PlantUML)
- `docs/data_flow_diagram.md` - data flow diagram (PlantUML)
- `docs/docker_compose_azure_local_dev.md` - Azurite-backed Docker Compose development notes
