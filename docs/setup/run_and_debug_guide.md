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
- `duckdb`: included as a dependency, not currently required by the main runtime path
- `sqlalchemy`, `psycopg[binary]`: PostgreSQL connectivity
- `alembic`: PostgreSQL schema versioning and bootstrap
- `streamlit`, `plotly`: dashboard
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

Important:

- PostgreSQL is optional on this branch.
- The dashboard reads the Parquet file, not Postgres.
- For runnig the application locally without Docker, the simplest supported setup is `USE_POSTGRES=0`.
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

# Optional cloud storage settings left unused in local Parquet flow
GOLD_STORAGE_BACKEND=local
AZURE_BLOB_CONTAINER=
AZURE_GOLD_PREFIX=
AZURE_STORAGE_CONNECTION_STRING=
AZURE_STORAGE_ACCOUNT_NAME=
AZURE_STORAGE_ACCOUNT_KEY=

# Optional Postgres load
USE_POSTGRES=0
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=cityair
POSTGRES_USER=cityair
POSTGRES_PASSWORD=cityair

# ---- Dashboard ----
DASHBOARD_DATA_PATH=./data/gold/air_pollution_gold.parquet
```

### Why these local values matter

- `CITIES_SOURCE=postgres` makes PostgreSQL the runtime source of truth for city selection.
- `CITIES_FILE=configs/cities.csv` points the seed/import workflow to the checked-in city list on your machine.
- `DATA_DIR`, `RAW_DIR`, and `GOLD_DIR` must use local paths, not `/app/...` container paths.
- `DASHBOARD_DATA_PATH` must point to the Parquet file created by the local pipeline run.
- `USE_POSTGRES=0` prevents the pipeline from trying to connect to a Postgres server you may not have running.

### Exact commands to run locally without Docker

After your virtual environment is active and `.env` matches the values above:

1. Seed cities into PostgreSQL:

```bash
python -m pipeline.cli --seed-cities
```

2. Run the pipeline:

```bash
python services/pipeline/run_pipeline.py --source openweather --history-hours 72
```

3. Start the dashboard:

```bash
streamlit run services/dashboard/app/Home.py
```

4. Open the dashboard:

```text
http://localhost:8501
```

### How to verify the local non-Docker run worked

These are the expected results:

- `data/raw` contains raw OpenWeather responses and manifests
- `data/gold/air_pollution_gold.parquet` exists
- the Streamlit app starts without the "Gold dataset not found" warning
- the dashboard shows row and city metrics

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
CITIES_FILE=configs/cities.csv
DATA_DIR=./data
RAW_DIR=./data/raw
GOLD_DIR=./data/gold
DASHBOARD_DATA_PATH=./data/gold/air_pollution_gold.parquet
USE_POSTGRES=0
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
      "program": "${workspaceFolder}/services/pipeline/run_pipeline.py",
      "console": "integratedTerminal",
      "cwd": "${workspaceFolder}",
      "args": ["--source", "openweather", "--history-hours", "72"],
      "env": {
        "OPENWEATHER_API_KEY": "YOUR_REAL_KEY",
        "HISTORY_HOURS": "72",
        "MAX_CALLS_PER_MINUTE": "50",
        "CITIES_FILE": "${workspaceFolder}/configs/cities.csv",
        "DATA_DIR": "${workspaceFolder}/data",
        "RAW_DIR": "${workspaceFolder}/data/raw",
        "GOLD_DIR": "${workspaceFolder}/data/gold",
        "USE_POSTGRES": "0",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "cityair",
        "POSTGRES_USER": "cityair",
        "POSTGRES_PASSWORD": "cityair"
      }
    },
    {
      "name": "Dashboard: Streamlit",
      "type": "debugpy",
      "request": "launch",
      "module": "streamlit",
      "console": "integratedTerminal",
      "cwd": "${workspaceFolder}",
      "args": [
        "run",
        "services/dashboard/app/Home.py",
        "--server.port",
        "8501",
        "--server.address",
        "127.0.0.1"
      ],
      "env": {
        "DASHBOARD_DATA_PATH": "${workspaceFolder}/data/gold/air_pollution_gold.parquet"
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
   - `services/pipeline/run_pipeline.py`
   - `services/pipeline/src/pipeline/extract/geocoding.py`
   - `services/pipeline/src/pipeline/extract/openweather_air_pollution.py`
   - `services/pipeline/src/pipeline/transform/openweather_air_pollution_transform.py`
6. Start debugging with `F5`.
7. After the pipeline has created the Parquet output, run `Dashboard: Streamlit` if you also want to debug the UI process.

### How to verify local debugging is working

For the pipeline:

- breakpoints are hit
- output files appear under `data/raw` and `data/gold`
- the run ends without a traceback

For the dashboard:

- VS Code starts Streamlit without import errors
- <http://127.0.0.1:8501> opens successfully
- the dashboard shows row and city counts instead of the "Gold dataset not found" warning

## 5. Docker Compose setup and launch

If you want to run the project with Docker Compose, you do not need to install Python libraries on your host machine. The containers install the Python dependencies during the image build.

You do need:

- Docker Desktop for your OS
- Docker Compose support
- An OpenWeather API key
- Internet access so Docker can pull/build images and the app can call the OpenWeather APIs
- The project checked out locally

For this repository, Docker Compose starts these services:

- `pipeline`: one-time ETL job that fetches air-quality data and writes output files
- `dashboard`: Streamlit UI on port `8501`
- `postgres`: PostgreSQL on port `5432`
- `adminer`: Adminer UI on port `8080`

Important behavior:

- The `pipeline` container is expected to finish and exit after it completes successfully.
- The `dashboard`, `postgres`, and `adminer` containers should stay running.

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
DASHBOARD_DATA_PATH=/app/data/gold/air_pollution_gold.parquet
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

#### Step 7: Check whether the application is running properly

Run:

```bash
docker compose ps
```

Expected result on a healthy run:

- `dashboard` is `Up`
- `postgres` is `Up`
- `adminer` is `Up`
- `pipeline` may show `Exited (0)` after finishing, and that is expected

Check container logs:

```bash
docker compose logs pipeline
docker compose logs dashboard
```

Healthy signs:

- The pipeline logs end without a traceback
- The pipeline logs include completion output
- The dashboard logs show Streamlit started successfully

#### Step 8: Verify outputs

After the pipeline finishes, these checks should pass:

1. The gold data file exists at `data/gold/air_pollution_gold.parquet`.
2. The raw cache exists under `data/raw`.
3. The dashboard opens at <http://localhost:8501>.
4. Adminer opens at <http://localhost:8080>.

Optional checks:

```bash
docker compose exec postgres psql -U cityair -d cityair -c "\\dt"
```

Notes:

- On this branch, Postgres and Adminer start even when `USE_POSTGRES=0`.
- The pipeline only writes to Postgres if `USE_POSTGRES=1` is set in `.env`.

#### Step 9: Stop the application

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

#### The dashboard page says the gold dataset was not found

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
- `5432` for Postgres

If one of those ports is already in use, stop the other app or change the port mapping in `docker-compose.yml`.

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
- `services/dashboard/app/Home.py`

Official external docs:

- Docker Compose install overview: <https://docs.docker.com/compose/install/>
- Docker Desktop Windows install: <https://docs.docker.com/desktop/setup/install/windows-install/>
- Docker Desktop Mac install: <https://docs.docker.com/desktop/setup/install/mac-install/>
- VS Code Python debugging: <https://code.visualstudio.com/docs/python/debugging>
- Python downloads: <https://www.python.org/downloads/>
