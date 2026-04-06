# Docker And Compose Walkthrough

This guide explains the Docker-related files in this repository line by line.

It is written for beginners who want to understand what each instruction is doing instead of only copying commands.

The files covered here are:

- `services/pipeline/Dockerfile`
- `services/dashboard/Dockerfile`
- `docker-compose.yml`

This walkthrough also explains how the local Azure Blob emulator and browser-based storage explorer fit into the stack.

## `services/pipeline/Dockerfile`

Current file:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY services/pipeline /app
COPY configs /app/configs

ENV PYTHONUNBUFFERED=1
CMD ["python", "run_pipeline.py", "--source", "openweather", "--history-hours", "72"]
```

Line-by-line explanation:

- `FROM python:3.11-slim`
  Starts the image from the official Python 3.11 slim base image.
  "Slim" means it is smaller than the full Python image, which helps reduce image size.

- `WORKDIR /app`
  Sets `/app` as the working directory inside the container.
  Commands that follow run relative to this folder unless they use absolute paths.

- `RUN apt-get update && apt-get install -y --no-install-recommends \`
  Updates the Debian package list and installs system packages needed during image build.

- `    build-essential \`
  Installs common C/C++ build tools.
  This is often needed because some Python packages compile native extensions during `pip install`.

- ` && rm -rf /var/lib/apt/lists/*`
  Deletes cached package-list files after installation.
  This keeps the image smaller.

- `COPY requirements.txt /app/requirements.txt`
  Copies the Python dependency file from the repo into the image.

- `RUN pip install --no-cache-dir -r /app/requirements.txt`
  Installs the Python dependencies listed in `requirements.txt`.
  `--no-cache-dir` tells pip not to keep downloaded package caches, which again helps keep the image smaller.

- `COPY services/pipeline /app`
  Copies the pipeline application code into the container.

- `COPY configs /app/configs`
  Copies the configuration files, including the cities CSV, into the container.

- `ENV PYTHONUNBUFFERED=1`
  Makes Python send logs to stdout immediately instead of buffering them.
  That is helpful in containers because logs appear in `docker compose logs` right away.

- `CMD ["python", "run_pipeline.py", "--source", "openweather", "--history-hours", "72"]`
  Sets the default command when the pipeline container starts.
  In this project, it runs the ETL pipeline using the OpenWeather source and a 72-hour history window.

## `services/dashboard/Dockerfile`

Current file:

```dockerfile
FROM node:20-alpine AS frontend-builder

WORKDIR /frontend
COPY services/dashboard/frontend/package.json ./package.json
COPY services/dashboard/frontend/vite.config.js ./vite.config.js
COPY services/dashboard/frontend/index.html ./index.html
COPY services/dashboard/frontend/src ./src
RUN npm install
RUN npm run build

FROM python:3.11-slim

WORKDIR /app
COPY services/dashboard/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY services/dashboard/server.py /app/server.py
COPY --from=frontend-builder /frontend/dist /app/static
EXPOSE 8501
CMD ["python", "server.py"]
```

Line-by-line explanation:

- `FROM node:20-alpine AS frontend-builder`
  Starts a frontend build stage for the React dashboard assets.

- `WORKDIR /frontend`
  Sets the working directory for the frontend build.

- `COPY services/dashboard/frontend/package.json ./package.json`
  Copies the React frontend package definition.

- `COPY services/dashboard/frontend/vite.config.js ./vite.config.js`
  Copies the Vite configuration.

- `COPY services/dashboard/frontend/index.html ./index.html`
  Copies the frontend HTML entrypoint.

- `COPY services/dashboard/frontend/src ./src`
  Copies the React source files.

- `RUN npm install`
  Installs the frontend build dependencies.

- `RUN npm run build`
  Produces the static React build under `dist/`.

- `FROM python:3.11-slim`
  Starts the runtime image for the dashboard server.

- `WORKDIR /app`
  Sets `/app` as the working directory inside the container.

- `COPY services/dashboard/requirements.txt /app/requirements.txt`
  Copies the dashboard server dependencies into the image.

- `RUN pip install --no-cache-dir -r /app/requirements.txt`
  Installs the Python dependencies needed by the dashboard server.

- `COPY services/dashboard/server.py /app/server.py`
  Copies the Python dashboard server into the image.

- `COPY --from=frontend-builder /frontend/dist /app/static`
  Copies the built React frontend assets into the runtime image.

- `EXPOSE 8501`
  Documents that the container listens on port `8501`.
  This does not publish the port by itself; Docker Compose does that later.

- `CMD ["python", "server.py"]`
  Sets the default command for the dashboard container.
  It launches the Python dashboard server, which serves the React frontend and the PostgreSQL-backed dashboard API.

## `docker-compose.yml`

Current file:

```yaml
services:
  pipeline:
    build:
      context: .
      dockerfile: services/pipeline/Dockerfile
    env_file: .env
    volumes:
      - ./data:/app/data
      - ./configs:/app/configs:ro
    depends_on:
      - postgres
    command: ["python", "run_pipeline.py", "--source", "openweather", "--history-hours", "72"]
    restart: "no"

  dashboard:
    build:
      context: .
      dockerfile: services/dashboard/Dockerfile
    env_file: .env
    volumes:
      - ./data:/app/data:ro
      - ./configs:/app/configs:ro
    ports:
      - "8501:8501"
    depends_on:
      - pipeline
    command: ["streamlit", "run", "app/Home.py", "--server.port=8501", "--server.address=0.0.0.0"]

  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: cityair
      POSTGRES_USER: cityair
      POSTGRES_PASSWORD: cityair
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  adminer:
    image: adminer:4
    ports:
      - "8080:8080"
    depends_on:
      - postgres

volumes:
  postgres_data:
```

### Top-level structure

- `services:`
  Starts the list of containers that Docker Compose should manage together.

In this project, there are seven services:

- `pipeline`
- `dashboard`
- `postgres`
- `adminer`
- `azurite`
- `azurestorageexplorer`
- `migrate`

`azurite` is a local Azure Storage emulator. It allows the pipeline to test Azure Blob uploads without requiring a real Azure account.
`azurestorageexplorer` is a browser-based UI that connects to Azurite so you can verify uploaded blobs from a web page.

### `pipeline` service

- `pipeline:`
  Names the service.

- `build:`
  Tells Docker Compose to build an image instead of pulling a finished image from a registry.

- `context: .`
  Uses the project root as the Docker build context.
  That means files from the repo root are available to copy into the image.

- `dockerfile: services/pipeline/Dockerfile`
  Tells Compose exactly which Dockerfile to use for the pipeline service.

- `env_file: .env`
  Loads environment variables from the project’s `.env` file into the container.

- `volumes:`
  Defines host-to-container filesystem mounts.

- `- ./data:/app/data`
  Mounts the host `data` folder into the container as `/app/data`.
  This lets pipeline outputs remain on the host machine after the container stops.

- `- ./configs:/app/configs:ro`
  Mounts the host `configs` folder into the container as `/app/configs`.
  `:ro` means read-only, so the container can read config files but not modify them.

- `depends_on:`
  Lists services that should start before this one.

- `- postgres`
  Indicates the pipeline depends on Postgres being started first.

- `- migrate`
  Ensures schema migrations are run before the batch job starts.

- `- azurite`
  Makes the local Blob emulator available when Azure Blob publishing is enabled.

- `command: ["python", "-m", "pipeline.cli", "--source", "openweather", "--history-hours", "72"]`
  Runs the packaged pipeline module instead of the older script-style entrypoint.

- `restart: "no"`
  Tells Docker not to restart this service automatically.
  That makes sense because the pipeline is a batch job, not a long-running web service.

### `dashboard` service

- `dashboard:`
  Names the dashboard service.

- `build:`
  Builds the dashboard image from source.

- `context: .`
  Uses the repo root as the build context.

- `dockerfile: services/dashboard/Dockerfile`
  Uses the dashboard Dockerfile.

- `env_file: .env`
  Loads environment variables from `.env`.

- `volumes:`
  Defines host mounts for the dashboard.

- `- ./data:/app/data:ro`
  Mounts the data folder read-only.
  This is now mostly a compatibility mount rather than the dashboard's primary data path.

- `- ./configs:/app/configs:ro`
  Mounts the config folder read-only.

- `ports:`
  Publishes container ports to the host machine.

- `- "8501:8501"`
  Maps host port `8501` to container port `8501`.
  That is why the dashboard is available at `http://localhost:8501`.

- `depends_on:`
  Lists services that should start first.

- `- pipeline`
  Starts the dashboard after the pipeline service is started.
  Note that this does not guarantee the pipeline has finished producing data; it only controls startup order.

- `command: ["python", "server.py"]`
  Starts the Python dashboard server, which serves the React frontend and dashboard API.

### `postgres` service

- `postgres:`
  Names the Postgres database service.

- `image: postgres:16`
  Pulls the official Postgres version 16 image from Docker Hub.

- `environment:`
  Sets environment variables for the Postgres container.

- `POSTGRES_DB: cityair`
  Creates a default database named `cityair`.

- `POSTGRES_USER: cityair`
  Sets the database username.

- `POSTGRES_PASSWORD: cityair`
  Sets the database password.

- `ports:`
  Publishes database access to the host.

- `- "5432:5432"`
  Maps the standard Postgres port from the container to the host.

- `volumes:`
  Defines persistent storage for the database.

- `- postgres_data:/var/lib/postgresql/data`
  Stores Postgres data in a named Docker volume so the database survives container restarts.

### `adminer` service

- `adminer:`
  Names the Adminer service.

- `image: adminer:4`
  Pulls the Adminer image.
  Adminer is a lightweight web UI for inspecting databases.

- `ports:`
  Publishes Adminer on the host.

- `- "8080:8080"`
  Makes Adminer available at `http://localhost:8080`.

- `depends_on:`
  Starts Adminer after Postgres is started.

- `- postgres`
  Indicates the dependency.

### `azurite` service

- `azurite:`
  Names the Azure Storage emulator service.

- `image: mcr.microsoft.com/azure-storage/azurite`
  Pulls the official Azurite image.

- `command: ["azurite-blob", "--blobHost", "0.0.0.0", "--blobPort", "10000", "--location", "/data"]`
  Starts the Blob emulator endpoint and stores emulator data under `/data`.

- `ports:`
  Publishes the Blob emulator to the host.

- `- "10000:10000"`
  Makes the Blob endpoint reachable on `http://localhost:10000`.

- `volumes:`
  Persists emulator state across restarts.

- `- azurite_data:/data`
  Stores Blob emulator data in a named Docker volume.

### `azurestorageexplorer` service

- `azurestorageexplorer:`
  Names the browser-based Azure Storage explorer service.

- `image: sebagomez/azurestorageexplorer:3.1.0`
  Pulls a third-party web UI for browsing Azure Storage-compatible services.

- `ports:`
  Publishes the explorer UI on the host.

- `- "8081:8080"`
  Makes the explorer available at `http://localhost:8081`.

- `environment:`
  Preconfigures the explorer for the local Azurite setup.

- `AZURITE: "true"`
  Tells the explorer it is connecting to Azurite rather than a standard Azure public endpoint.

- `AZURE_STORAGE_CONNECTIONSTRING: ${AZURE_STORAGE_CONNECTION_STRING}`
  Reuses the same connection string that the pipeline uses for Blob uploads.

- `depends_on:`
  Starts the explorer after Azurite has started.

- `azurite:`
  Declares the dependency on the Blob emulator.

### `migrate` service

- `migrate:`
  Names the one-time schema migration service.

- `command: ["alembic", "upgrade", "head"]`
  Applies the latest PostgreSQL schema before the pipeline starts.

- `restart: "no"`
  Runs once and exits after migrations complete.

### Named volumes

- `volumes:`
  Starts the named-volume section.

- `postgres_data:`
  Declares a named Docker volume used by the Postgres service.

- `azurite_data:`
  Declares a named Docker volume used by the Azurite service.

## Practical summary

When you run:

```bash
docker compose up --build
```

Docker Compose does the following:

1. builds the pipeline and dashboard images
2. starts Postgres
3. waits until Postgres passes its healthcheck
4. starts Azurite for local Blob uploads
5. runs schema migration
6. starts the pipeline job only after migration succeeds
7. starts the React dashboard server
8. starts Adminer
9. starts the browser-based Azure Storage explorer

The important idea is that:

- the pipeline writes data into `./data`
- the pipeline can also upload the gold Parquet artifact into Azurite when Azure Blob publishing is enabled
- the dashboard primarily reads PostgreSQL through its backend API
- `./data` remains useful for optional compatibility exports
- Adminer helps you inspect Postgres visually
- the browser explorer lets you verify the Blob artifact under container `gold` and path `exports/`

## Azurite verification flow

Use this sequence to verify the local Azure Blob path after running `docker compose up --build`:

1. Confirm the pipeline completed successfully:

```bash
docker compose logs pipeline
```

2. Confirm Azurite accepted the upload:

```bash
docker compose logs azurite --tail=200
```

Healthy log lines include:

```text
PUT /devstoreaccount1/gold?restype=container ... 201
PUT /devstoreaccount1/gold/exports/air_pollution_gold.parquet ... 201
```

3. Open the browser explorer:

```text
http://localhost:8081
```

4. Browse to:

- container: `gold`
- path: `exports/`
- blob: `air_pollution_gold.parquet`

5. If the explorer shows `0 objects`, clear the path and retry with `exports/`.
Do not use `gold/exports/` inside the selected `gold` container.
