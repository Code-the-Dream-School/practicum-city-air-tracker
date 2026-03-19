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

Stop services:

```bash
docker compose down
```

Docker note: you do not need your host `.venv` when running with Docker Compose. Each container installs Python dependencies inside the image (see `services/pipeline/Dockerfile` and `services/dashboard/Dockerfile`).

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

## Configure cities

The pipeline reads city targets from a CSV file controlled by the `CITIES_FILE`
environment variable. The default is `CITIES_FILE=/app/configs/cities.csv`, which
maps to `./configs/cities.csv` on your host machine (mounted read-only into both
the `pipeline` and `dashboard` containers via `docker-compose.yml`).

The rows below are **sample cities included as editable examples only** — replace
them with the cities you want to track:
```
city,country_code,state
Toronto,CA,
Paris,FR,
Lagos,NG,
Sydney,AU,NSW
```

> For global cities, **`country_code` is required** to disambiguate
> (e.g. `Springfield,US,IL`). The `state` column is optional for most countries.

### Editing cities (Docker)

Because `./configs` is mounted **read-only** into the containers, always edit the
CSV on your **host machine** before running the pipeline — not inside the container:
```bash
# Edit on your host, then run
nano configs/cities.csv
docker compose up --build
```

### Using a custom city file (`CITIES_FILE`)

You can point the pipeline to any CSV that follows the format above by changing
`CITIES_FILE` in your `.env`. This is useful for maintaining separate city lists
per environment.

**Local dev `.env`:**
```
CITIES_FILE=configs/cities_local.csv
```

**Docker `.env` (path must be the container path under `/app/configs/`):**
```
CITIES_FILE=/app/configs/cities_production.csv
```

> **Note:** Any custom file must live inside `./configs/` on your host so it is
> included in the read-only volume mount (`./configs:/app/configs:ro`).

**Inline at the command line (local Python only):**
```bash
CITIES_FILE=configs/cities_staging.csv \
  python services/pipeline/run_pipeline.py --source openweather --history-hours 72
```

### Troubleshooting city config issues

| Symptom | Likely cause | Fix |
|---|---|---|
| `FileNotFoundError` on startup | `CITIES_FILE` path does not exist or is misspelled | Verify the file exists on your host under `./configs/`; remember the container sees it as `/app/configs/` |
| Custom file not found in Docker | File is outside `./configs/` on the host | Move the file inside `./configs/` — only that directory is volume-mounted into the containers |
| Pipeline runs but produces no output | CSV is empty or has only a header row | Add at least one data row beneath the `city,country_code,state` header |
| Unexpected cities appear in output | `CITIES_FILE` points to the wrong file | Run `docker compose exec pipeline env \| grep CITIES_FILE` to confirm the active value |
| Geocoding fails for a city | Missing or incorrect `country_code` | Add the correct ISO 3166-1 alpha-2 code (e.g. `US`, `FR`, `NG`) |

## Notes for Team Collaboration

- `.venv` is local and should not be committed.
- One teammate can use `venv` while another uses global Python; code and commands stay the same once Python dependencies are installed.
- Prefer `python -m pip ...` for cross-platform consistency.

## Docs / Diagrams

- `docs/architecture.md` - component + sequence diagrams (PlantUML)
- `docs/data_flow_diagram.md` - data flow diagram (PlantUML)
- `docs/docker_and_compose_walkthrough.md` - line-by-line explanation of the Dockerfiles and `docker-compose.yml`
- `docs/github_feature_branch_pr_guide.md` - feature branch and pull request workflow guide
- `docs/pr_review_best_practices.md` - project-specific pull request review guidance
- `docs/react_dashboard_architecture_guide.md` - architecture and library guide for the React dashboard implementation on `AIR-007.1`
- `docs/what_is_a_data_pipeline.md` - plain-language explanation of what a data pipeline is and why teams use one
