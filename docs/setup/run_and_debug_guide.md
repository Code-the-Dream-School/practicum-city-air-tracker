# City Air Tracker Run And Debug Guide

This guide is based on the current `main` branch as checked on 2026-03-23.

## 1. Local Python setup and libraries

These are the Python dependencies currently declared in `requirements.txt`:

- `pandas>=2.2`
- `pyarrow>=16.0`
- `requests>=2.32`
- `pydantic>=2.7`
- `pydantic-settings>=2.3`
- `python-dotenv>=1.0`
- `duckdb>=1.0`
- `sqlalchemy>=2.0`
- `alembic>=1.13`
- `psycopg[binary]>=3.2`
- `streamlit>=1.36`
- `plotly>=5.22`
- `pytest>=8.2`

What they are used for on this branch:

- `pandas`, `pyarrow`: CSV and Parquet data handling
- `requests`: OpenWeather API calls
- `pydantic`, `pydantic-settings`, `python-dotenv`: environment/config loading
- `azure-storage-blob`: optional Azure Blob upload for the gold Parquet artifact
- `duckdb`: included as a dependency, not currently required by the main runtime path
- `sqlalchemy`, `psycopg[binary]`: PostgreSQL connectivity
- `alembic`: PostgreSQL schema versioning and bootstrap
- dashboard frontend assets are built with the React/Vite app under `services/dashboard/frontend`
- the dashboard Python server lives in `services/dashboard/server.py`
- `pytest`: tests

## 2. How to install Python and the Python libraries

These steps are for local development or VS Code debugging. They are not required for Docker Compose-only usage.

The repo README says Python `3.11+` is supported, and `3.12` is currently used in this workspace. A safe choice is Python `3.12`.

Official Python downloads:

- Windows and macOS downloads: <https://www.python.org/downloads/>


### Windows

1. Install Python from the official Python downloads page.
2. Open PowerShell in the project root.
3. Create a virtual environment:

```powershell
py -m venv .venv
```

4. Activate it:

```powershell
.venv\Scripts\Activate.ps1
```

5. Upgrade packaging tools:

```powershell
python -m pip install --upgrade pip setuptools wheel
```

6. Install project dependencies:

```powershell
python -m pip install -r requirements.txt
```

### macOS

1. Install Python from the official Python downloads page.
2. Open Terminal in the project root.
3. Create a virtual environment:

```bash
python3 -m venv .venv
```

4. Activate it:

```bash
source .venv/bin/activate
```

5. Upgrade packaging tools:

```bash
python -m pip install --upgrade pip setuptools wheel
```

6. Install project dependencies:

```bash
python -m pip install -r requirements.txt
```

## 3. Run locally without Docker

If you want to run this project locally without Docker, use Python plus a virtual environment and set `.env` to local filesystem paths.

For the most direct DB-first setup and validation path, use [local_postgresql_first_workflow.md](/home/eugen/code-the-dream-workspace/practicum-city-air-tracker/docs/setup/local_postgresql_first_workflow.md) alongside this guide.

Important:

- PostgreSQL is the primary gold-data target on this branch.
- The React dashboard reads PostgreSQL-backed data through the dashboard server API.
- For running the application locally without Docker, you should have PostgreSQL available and keep `USE_POSTGRES=1`.
- The checked-in `.env.example` is Docker-oriented, so you must change it for local runs.

### Exact `.env` values for local-without-Docker

Create `.env` from `.env.example`, then make it match this:

```dotenv
# ---- Pipeline ----
OPENWEATHER_API_KEY=YOUR_REAL_KEY
HISTORY_HOURS=72
MAX_CALLS_PER_MINUTE=50
CITIES_SOURCE=postgres
CITIES_FILE=configs/cities.csv

# Local paths (non-Docker)
DATA_DIR=./data
RAW_DIR=./data/raw
GOLD_DIR=./data/gold

# PostgreSQL is the primary gold target
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

### Why these local values matter

- `CITIES_SOURCE=postgres` makes PostgreSQL the runtime source of truth for city selection.
- `CITIES_FILE=configs/cities.csv` points the seed/import workflow to the checked-in city list on your machine.
- `DATA_DIR`, `RAW_DIR`, and `GOLD_DIR` must use local paths, not `/app/...` container paths.
- `USE_POSTGRES=1` keeps PostgreSQL as the primary gold-data target during local runs.
- `WRITE_GOLD_PARQUET=0` keeps Parquet export disabled unless you explicitly want a secondary file artifact.
- `WRITE_GOLD_AZURE_BLOB=0` keeps Azure Blob publishing disabled unless you explicitly want to test the Blob upload path.
- when Blob publishing is enabled, you can point the same settings at either local Azurite or real Azure Blob Storage; see [azure_blob_storage_configuration.md](./azure_blob_storage_configuration.md)

### Exact commands to run locally without Docker

After your virtual environment is active and `.env` matches the values above:

1. Seed cities into PostgreSQL:

```bash
python -m pipeline.cli --seed-cities
```

2. Run the pipeline:

```bash
python -m pipeline.cli --source openweather --history-hours 72
```

3. Start the dashboard:

```bash
python services/dashboard/server.py
```

4. Open the dashboard:

```text
http://localhost:8501
```

### How to verify the local non-Docker run worked

These are the expected results:

- PostgreSQL stores raw OpenWeather air-pollution responses and extract metadata for the DB-first migration path
- PostgreSQL stores the gold dataset in `air_pollution_gold`
- `data/gold/air_pollution_gold.parquet` exists only if `WRITE_GOLD_PARQUET=1`
- Azure Blob publishing only runs if `WRITE_GOLD_AZURE_BLOB=1`
- the dashboard server starts successfully on port `8501`
- the dashboard shows row and city metrics

If you only want to validate the pipeline and database behavior, you can stop after the PostgreSQL verification steps in [local_postgresql_first_workflow.md](/home/eugen/code-the-dream-workspace/practicum-city-air-tracker/docs/setup/local_postgresql_first_workflow.md) and skip the dashboard.

## 4. How to run and debug the application in VS Code

VS Code debugging is for local Python execution, not for debugging inside the Docker containers.

### Install the needed VS Code extensions

Recommended:

- Python extension by Microsoft
- Python Debugger extension by Microsoft

Official VS Code Python debugging docs:

- <https://code.visualstudio.com/docs/python/debugging>

### Prepare a local Python environment

Install the Python dependencies using the steps in section 2, then open the project folder in VS Code and select the `.venv` interpreter.

### Important local-path note

The checked-in `.env.example` file uses Docker container paths such as `/app/data` and `/app/configs/cities.csv`.

For local VS Code debugging, use local filesystem paths instead. In a real `.env` file, use absolute paths or project-relative paths, not `${workspaceFolder}`.

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
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=cityair
POSTGRES_USER=cityair
POSTGRES_PASSWORD=cityair
```

Because `.env` is loaded by the app at runtime, the safest approach is either:

- temporarily edit `.env` for local debugging, or
- add the environment variables directly in `.vscode/launch.json`

### Recommended `launch.json`

Create `.vscode/launch.json` with content like this:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Pipeline: run current branch",
      "type": "debugpy",
      "request": "launch",
      "module": "pipeline.cli",
      "console": "integratedTerminal",
      "cwd": "${workspaceFolder}",
      "args": ["--source", "openweather", "--history-hours", "72"],
      "env": {
        "OPENWEATHER_API_KEY": "YOUR_REAL_KEY",
        "HISTORY_HOURS": "72",
        "MAX_CALLS_PER_MINUTE": "50",
        "CITIES_SOURCE": "postgres",
        "CITIES_FILE": "${workspaceFolder}/configs/cities.csv",
        "DATA_DIR": "${workspaceFolder}/data",
        "RAW_DIR": "${workspaceFolder}/data/raw",
        "GOLD_DIR": "${workspaceFolder}/data/gold",
        "USE_POSTGRES": "1",
        "WRITE_GOLD_PARQUET": "0",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "cityair",
        "POSTGRES_USER": "cityair",
        "POSTGRES_PASSWORD": "cityair"
      }
    },
    {
      "name": "Dashboard: React server",
      "type": "debugpy",
      "request": "launch",
      "program": "${workspaceFolder}/services/dashboard/server.py",
      "console": "integratedTerminal",
      "cwd": "${workspaceFolder}",
      "env": {
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "cityair",
        "POSTGRES_USER": "cityair",
        "POSTGRES_PASSWORD": "cityair"
      }
    }
  ]
}
```

### Debugging workflow in VS Code

1. Open the repo in VS Code.
2. Select the project interpreter from `.venv`.
3. Open Run and Debug.
4. Choose `Pipeline: run current branch`.
5. Set breakpoints in files such as:
   - `services/pipeline/src/pipeline/cli.py`
   - `services/pipeline/src/pipeline/extract/geocoding.py`
   - `services/pipeline/src/pipeline/extract/openweather_air_pollution.py`
   - `services/pipeline/src/pipeline/transform/openweather_air_pollution_transform.py`
6. Start debugging with `F5`.
7. If you also want to debug the dashboard, run `Dashboard: React server` after the pipeline has populated PostgreSQL.

### How to verify local debugging is working

For the pipeline:

- breakpoints are hit
- rows appear in PostgreSQL tables such as `pipeline_runs`, `raw_air_pollution_responses`, and `air_pollution_gold`
- the run ends without a traceback

For the dashboard:

- VS Code starts the dashboard server without import errors
- <http://127.0.0.1:8501> opens successfully
- the dashboard shows row and city counts loaded from PostgreSQL

## 5. Docker Compose setup and launch

If you want to run the project with Docker Compose, you do not need to install Python libraries on your host machine. The containers install the Python dependencies during the image build.

You do need:

- Docker Desktop for your OS
- Docker Compose support
- An OpenWeather API key
- Internet access so Docker can pull/build images and the app can call the OpenWeather APIs
- The project checked out locally

For this repository, Docker Compose starts these services:

- `pipeline`: one-time ETL job that fetches air-quality data and writes PostgreSQL-backed output
- `dashboard`: React frontend served by the Python dashboard server on port `8501`
- `postgres`: PostgreSQL on port `5432`
- `adminer`: Adminer UI on port `8080`
- `azurite`: local Azure Blob emulator on port `10000`
- `azurestorageexplorer`: browser-based Azure Storage explorer on port `8081`

Important behavior:

- The `pipeline` container is expected to finish and exit after it completes successfully.
- The `dashboard`, `postgres`, `adminer`, `azurite`, and `azurestorageexplorer` containers should stay running.

### How to install Docker Compose on Windows and macOS

For Windows and macOS, the recommended install path is Docker Desktop. Docker’s official docs state that Docker Desktop includes Docker Compose.

Official Docker sources:

- Docker Compose install overview: <https://docs.docker.com/compose/install/>
- Install Docker Desktop on Windows: <https://docs.docker.com/desktop/setup/install/windows-install/>
- Install Docker Desktop on Mac: <https://docs.docker.com/desktop/setup/install/mac-install/>

#### Windows

1. Download Docker Desktop from Docker’s Windows install page.
2. Run `Docker Desktop Installer.exe`.
3. Follow the installer prompts.
4. Start Docker Desktop after installation.
5. Verify installation:

```powershell
docker --version
docker compose version
```

Notes from Docker’s Windows docs:

- Docker Desktop on Windows may require WSL 2 depending on your setup.
- Docker’s install page walks through the WSL-related prerequisites.

#### macOS

1. Download Docker Desktop from Docker’s Mac install page.
2. Open `Docker.dmg`.
3. Drag Docker into the Applications folder.
4. Start Docker Desktop from Applications.
5. Verify installation:

```bash
docker --version
docker compose version
```

### Steps to run the application with Docker Compose

#### Step 1: Check out the `main` branch

```bash
git checkout main
git pull
```

#### Step 2: Make sure Docker Desktop is running

Start Docker Desktop and wait until it reports that Docker is running.

#### Step 3: Create your `.env` file

From the project root:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

#### Step 4: Set your OpenWeather API key

Edit `.env` and replace:

```dotenv
OPENWEATHER_API_KEY=CHANGEME
```

with your real key.

For Docker Compose on this branch, the default `.env.example` paths are already set correctly:

```dotenv
CITIES_FILE=/app/configs/cities.csv
DATA_DIR=/app/data
RAW_DIR=/app/data/raw
GOLD_DIR=/app/data/gold
```

#### Step 5: Review or edit the city list

Edit `configs/cities.csv` on your host machine.

Expected columns:

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

- `country_code` is required for reliable geocoding.
- The `configs` folder is mounted read-only into the containers, so edit the file on your machine, not inside a container.

#### Step 6: Build and start the stack

From the repo root:

```bash
docker compose up --build
```

If you prefer detached mode:

```bash
docker compose up --build -d
```

If you want a completely fresh local state for PostgreSQL and Azurite, use:

```bash
docker compose down -v
docker compose up --build
```

#### Step 7: Check whether the application is running properly

Run:

```bash
docker compose ps
```

Expected result on a healthy run:

- `dashboard` is `Up`
- `postgres` is `Up`
- `adminer` is `Up`
- `azurite` is `Up`
- `azurestorageexplorer` is `Up`
- `migrate` should show `Exited (0)` after applying the schema
- `pipeline` may show `Exited (0)` after finishing, and that is expected

Check container logs:

```bash
docker compose logs pipeline
docker compose logs dashboard
```

Healthy signs:

- The pipeline logs end without a traceback
- The pipeline logs include completion output
- The dashboard logs show the dashboard server started successfully
- The Azurite logs show Blob API requests if Blob publishing is enabled

#### Step 8: Verify Azurite Blob publishing

Use this sequence when `WRITE_GOLD_AZURE_BLOB=1`.

1. Confirm the pipeline completed successfully:

```bash
docker compose logs pipeline
```

2. Confirm Azurite received the Blob upload:

```bash
docker compose logs azurite --tail=200
```

Healthy signs include log lines like:

```text
PUT /devstoreaccount1/gold?restype=container ... 201
PUT /devstoreaccount1/gold/exports/air_pollution_gold.parquet ... 201
```

3. Open the browser explorer:

```text
http://localhost:8081
```

The explorer is preconfigured for Azurite through Docker Compose and should open already authenticated.

4. Browse to the uploaded artifact:

- container: `gold`
- path inside container: `exports/`
- blob name: `air_pollution_gold.parquet`

The full blob path is:

```text
gold / exports/air_pollution_gold.parquet
```

Important:

- `gold` is the container name
- the path inside that container is `exports/`
- do not use `gold/exports/` as the path inside the explorer

5. Optional verification:

- download the blob from the explorer UI
- confirm the file is non-empty
- compare its size or contents with any local Parquet export if `WRITE_GOLD_PARQUET=1`

#### Step 9: Verify outputs

After the pipeline finishes, these checks should pass:

1. The gold data is available in PostgreSQL table `air_pollution_gold`.
2. The raw cache exists under `data/raw`.
3. The dashboard opens at <http://localhost:8501>.
4. Adminer opens at <http://localhost:8080>.
5. Azure Storage Explorer opens at <http://localhost:8081>.

Optional checks:

```bash
docker compose exec postgres psql -U cityair -d cityair -c "\\dt"
```

Notes:

- On this branch, Postgres is part of the normal runtime path and should stay enabled.
- Parquet export remains optional and only runs when `WRITE_GOLD_PARQUET=1`.
- Azure Blob publishing remains optional and only runs when `WRITE_GOLD_AZURE_BLOB=1`.
- The checked-in `.env.example` uses an Azurite connection string so Blob uploads can be tested locally through Docker Compose.

#### Step 10: Stop the application

```bash
docker compose down
```

If you also want to remove the named volume used by Postgres:

```bash
docker compose down -v
```

### Common Docker Compose troubleshooting

#### `docker compose` command is not found

- Docker Desktop is not installed correctly, or
- Docker Desktop is installed but not running

Check:

```bash
docker compose version
```

#### The dashboard API returns no rows

Likely causes:

- The `pipeline` container failed before writing output
- `OPENWEATHER_API_KEY` is missing or invalid
- The city file is empty or invalid

Check:

```bash
docker compose logs pipeline
```

#### The pipeline fails with API or network errors

Check:

- `OPENWEATHER_API_KEY` is set correctly in `.env`
- Your network can reach OpenWeather
- You are not hitting API rate limits

#### Port conflicts

This stack uses:

- `8501` for the dashboard
- `8080` for Adminer
- `8081` for the browser-based Azure Storage explorer
- `10000` for Azurite Blob storage
- `5432` for Postgres

If one of those ports is already in use, stop the other app or change the port mapping in `docker-compose.yml`.

#### The browser explorer shows `0 objects` but Azurite logs show `201`

This usually means the explorer is browsing the wrong path prefix.

Use:

- container: `gold`
- path: `exports/`

Do not use:

- `gold/exports/`

## 6. Source references used for this guide

Project files:

- `docker-compose.yml`
- `requirements.txt`
- `.env.example`
- `README.md`
- `services/pipeline/Dockerfile`
- `services/dashboard/Dockerfile`
- `services/pipeline/src/pipeline/common/config.py`
- `services/pipeline/src/pipeline/load/storage.py`
- `services/dashboard/server.py`

Official external docs:

- Docker Compose install overview: <https://docs.docker.com/compose/install/>
- Docker Desktop Windows install: <https://docs.docker.com/desktop/setup/install/windows-install/>
- Docker Desktop Mac install: <https://docs.docker.com/desktop/setup/install/mac-install/>
- VS Code Python debugging: <https://code.visualstudio.com/docs/python/debugging>
- Python downloads: <https://www.python.org/downloads/>
