# Fresh-Start Pipeline Bring-Up

This guide records the exact steps and commands used to bring up the City Air Tracker pipeline from a clean local Docker state and verify that:

- PostgreSQL is populated
- the gold Parquet artifact is uploaded to local Azure-compatible Blob storage through Azurite
- the dashboard is serving real data

## Goal

At the end of this sequence, the local environment should provide:

- PostgreSQL with seeded cities, raw responses, and gold rows
- Azurite with the uploaded blob at `gold / exports/air_pollution_gold.parquet`
- the dashboard available at `http://localhost:8501`
- the browser-based Blob explorer available at `http://localhost:8081`

## Important note about this run

During this verification session, the local machine could not rebuild Docker images because the Docker `buildx` plugin was missing.

Because of that, the fresh-start validation used the local fixed pipeline source mounted into the existing pipeline container image for the seed and ETL commands.

That means:

- PostgreSQL, Azurite, dashboard, and explorer still ran normally through Docker Compose
- the pipeline code path used the current local source tree mounted read-only into the container

This was the exact successful procedure used in the session.

## 1. Remove local containers and volumes

Start from a clean state:

```bash
docker compose down -v
```

This removes:

- Compose-managed containers
- the PostgreSQL named volume
- the Azurite named volume

## 2. Start the base services

Bring up the local database, migration, dashboard, Adminer, Azurite, and browser explorer:

```bash
docker compose up -d postgres azurite migrate dashboard adminer azurestorageexplorer
```

## 3. Confirm services are up

Check the service status:

```bash
docker compose ps
```

Healthy expected services:

- `postgres`
- `azurite`
- `dashboard`
- `adminer`
- `azurestorageexplorer`

## 4. Seed cities into PostgreSQL

Because this validation used the fixed local source tree mounted into the container, the city-seed command was run like this:

```bash
docker compose run --no-deps --rm -v "$PWD/services/pipeline/src:/workspace/pipeline_src:ro" pipeline sh -lc 'PYTHONPATH=/workspace/pipeline_src python -m pipeline.cli --seed-cities'
```

This loads the configured city CSV into the `cities` table in PostgreSQL.

## 5. Run the ETL pipeline

Run the full ETL pipeline against the clean local stack:

```bash
docker compose run --no-deps --rm -v "$PWD/services/pipeline/src:/workspace/pipeline_src:ro" pipeline sh -lc 'PYTHONPATH=/workspace/pipeline_src python -m pipeline.cli --source openweather --history-hours 72'
```

Expected log shape:

```text
INFO pipeline.orchestration - Starting pipeline
INFO pipeline.orchestration - Pipeline complete
```

## 6. Verify the Blob upload in Azurite

Check Azurite logs:

```bash
docker compose logs azurite --tail=100
```

Expected lines:

```text
PUT /devstoreaccount1/gold?restype=container HTTP/1.1" 201
PUT /devstoreaccount1/gold/exports/air_pollution_gold.parquet HTTP/1.1" 201
```

These confirm that:

- the `gold` container exists
- the Parquet blob was uploaded successfully

### Verify the archived Parquet file in the browser explorer

Open:

```text
http://localhost:8081
```

Then verify:

1. the `gold` container exists
2. the path `exports/` contains `air_pollution_gold.parquet`
3. the blob appears in the browser explorer list

Expected blob location:

- container: `gold`
- path: `exports/air_pollution_gold.parquet`

Important path note:

- inside the explorer, browse `exports/`
- do not use `gold/exports/` after the `gold` container is already selected

## 7. Verify PostgreSQL data

Check row counts and latest pipeline status:

```bash
docker exec practicum-city-air-tracker-postgres-1 psql -U cityair -d cityair -c "select count(*) as cities from cities; select count(*) as raw_rows from raw_air_pollution_responses; select count(*) as gold_rows from air_pollution_gold; select id, run_id, status, city_count, raw_response_count, gold_row_count from pipeline_runs order by id desc limit 3;"
```

Successful output from the verified run:

```text
cities = 4
raw_rows = 4
gold_rows = 288
status = succeeded
city_count = 4
gold_row_count = 288
```

### Verify that the PostgreSQL tables exist

Check that the DB-first schema was created:

```bash
docker exec practicum-city-air-tracker-postgres-1 psql -U cityair -d cityair -c "\dt"
```

Expected tables include:

- `cities`
- `geocoding_cache`
- `pipeline_runs`
- `raw_air_pollution_responses`
- `air_pollution_gold`

### Verify inserted city rows

```bash
docker exec practicum-city-air-tracker-postgres-1 psql -U cityair -d cityair -c "select id, city, country_code, state, is_active from cities order by id;"
```

Expected result:

- seeded city rows exist
- city count is greater than zero

### Verify inserted raw-response rows

```bash
docker exec practicum-city-air-tracker-postgres-1 psql -U cityair -d cityair -c "select id, city_id, request_start_utc, request_end_utc, record_count from raw_air_pollution_responses order by id;"
```

Expected result:

- one raw-response row exists per processed city for the requested window
- `record_count` is populated

### Verify inserted gold rows

```bash
docker exec practicum-city-air-tracker-postgres-1 psql -U cityair -d cityair -c "select geo_id, ts, aqi, aqi_category, risk_score from air_pollution_gold order by geo_id, ts limit 20;"
```

Expected result:

- gold rows exist
- timestamps, AQI values, categories, and risk scores are populated
- the data is queryable by the dashboard backend

## 8. Verify the dashboard API

Query the dashboard backend directly:

```bash
curl -s http://localhost:8501/api/dashboard | head -c 1200
```

Expected result:

- JSON payload is returned
- `rows` contains real data
- `summary` fields are populated

## 9. Open the local UIs

Blob explorer:

```text
http://localhost:8081
```

Expected blob location:

- container: `gold`
- path: `exports/air_pollution_gold.parquet`

Dashboard:

```text
http://localhost:8501
```

Adminer:

```text
http://localhost:8080
```

## Full command list

For convenience, here is the exact successful command sequence in order:

```bash
docker compose down -v
docker compose up -d postgres azurite migrate dashboard adminer azurestorageexplorer
docker compose ps
docker compose run --no-deps --rm -v "$PWD/services/pipeline/src:/workspace/pipeline_src:ro" pipeline sh -lc 'PYTHONPATH=/workspace/pipeline_src python -m pipeline.cli --seed-cities'
docker compose run --no-deps --rm -v "$PWD/services/pipeline/src:/workspace/pipeline_src:ro" pipeline sh -lc 'PYTHONPATH=/workspace/pipeline_src python -m pipeline.cli --source openweather --history-hours 72'
docker compose logs azurite --tail=100
docker exec practicum-city-air-tracker-postgres-1 psql -U cityair -d cityair -c "select count(*) as cities from cities; select count(*) as raw_rows from raw_air_pollution_responses; select count(*) as gold_rows from air_pollution_gold; select id, run_id, status, city_count, raw_response_count, gold_row_count from pipeline_runs order by id desc limit 3;"
curl -s http://localhost:8501/api/dashboard | head -c 1200
```

## Final verified state

From the successful run in this session:

- pipeline run id: `20260407T165520Z`
- cities: `4`
- raw rows: `4`
- gold rows: `288`
- blob path: `gold / exports/air_pollution_gold.parquet`
- dashboard API returned populated JSON

