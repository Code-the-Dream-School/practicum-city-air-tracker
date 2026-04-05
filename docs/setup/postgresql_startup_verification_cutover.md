# PostgreSQL Startup, Verification, and Cutover Guidance

This runbook documents how to start the PostgreSQL-first pipeline, verify that it is healthy, and manage the cutover from earlier file-first assumptions.

Use this guide when you need:

- a startup order for local or Docker-backed environments
- a verification checklist after bootstrap or rollout
- cutover checkpoints for PostgreSQL-first operation
- rollback guidance if the DB-first path fails

## Scope

This guide is about operational sequencing and validation.

It does not replace:

- [local_postgresql_first_workflow.md](/home/eugen/code-the-dream-workspace/practicum-city-air-tracker/docs/setup/local_postgresql_first_workflow.md) for day-to-day local development
- [postgresql_migrations_guide.md](/home/eugen/code-the-dream-workspace/practicum-city-air-tracker/docs/setup/postgresql_migrations_guide.md) for migration-tool details

## Startup order

The PostgreSQL-first pipeline should start in this order:

1. start PostgreSQL
2. apply Alembic migrations
3. seed cities into the `cities` table
4. run the pipeline
5. verify `pipeline_runs`, `raw_air_pollution_responses`, and `air_pollution_gold`
6. enable optional Parquet export only if you need dashboard compatibility

### Local Python startup

Use this when running the app directly on your machine:

```bash
alembic upgrade head
python -m pipeline.cli --seed-cities
python -m pipeline.cli --source openweather --history-hours 72
```

### Docker-backed startup

Use this when PostgreSQL or the app services are running through Docker Compose:

```bash
docker compose up -d postgres
docker compose run --rm migrate
docker compose run --rm pipeline python -m pipeline.cli --seed-cities
docker compose run --rm pipeline python run_pipeline.py --source openweather --history-hours 72
```

Notes:

- startup order matters more than whether the runtime is Docker or local Python
- the DB-first contract depends on schema readiness and seeded cities
- Parquet is not required for a successful pipeline run

## Verification checklist

After startup or rollout, verify the following in order.

### 1. Schema is current

```bash
alembic current
```

Or with SQL:

```bash
psql postgresql://cityair:cityair@localhost:5432/cityair -c "\dt"
```

Expected tables:

- `cities`
- `geocoding_cache`
- `pipeline_runs`
- `raw_air_pollution_responses`
- `air_pollution_gold`

### 2. Cities were seeded

```bash
psql postgresql://cityair:cityair@localhost:5432/cityair -c "select id, city, country_code, state, is_active from cities order by id;"
```

Expected result:

- at least one active city row exists
- city names and country codes match the intended seed CSV

### 3. Pipeline runs are recorded

```bash
psql postgresql://cityair:cityair@localhost:5432/cityair -c "select id, run_id, status, city_count, raw_response_count, gold_row_count from pipeline_runs order by id desc limit 5;"
```

Expected result:

- the latest run exists
- the latest run status is `succeeded`
- row counts are populated

### 4. Raw responses are present

```bash
psql postgresql://cityair:cityair@localhost:5432/cityair -c "select count(*) from raw_air_pollution_responses;"
```

Expected result:

- the count is greater than zero after a successful run

Optional spot check:

```bash
psql postgresql://cityair:cityair@localhost:5432/cityair -c "select city_id, request_start_utc, request_end_utc, record_count from raw_air_pollution_responses order by id desc limit 5;"
```

### 5. Gold rows are present

```bash
psql postgresql://cityair:cityair@localhost:5432/cityair -c "select count(*) from air_pollution_gold;"
```

Expected result:

- the count is greater than zero after a successful run

Optional spot check:

```bash
psql postgresql://cityair:cityair@localhost:5432/cityair -c "select geo_id, ts, aqi, aqi_category, pipeline_run_id from air_pollution_gold order by ts desc limit 10;"
```

### 6. Reruns remain safe

Run the pipeline again with the same window, then verify:

```bash
psql postgresql://cityair:cityair@localhost:5432/cityair -c "select count(*) from raw_air_pollution_responses;"
psql postgresql://cityair:cityair@localhost:5432/cityair -c "select count(*) from air_pollution_gold;"
```

Expected result:

- `raw_air_pollution_responses` should not grow for the same city/window request
- `air_pollution_gold` should remain deduplicated on `(geo_id, ts)`
- `pipeline_runs` should show the new run and its status

## Cutover guidance

Use this sequence when moving a shared environment from earlier file-first expectations to the PostgreSQL-first contract.

### Cutover order

1. apply the current migrations
2. verify PostgreSQL connectivity
3. seed or refresh `cities`
4. run one validation pipeline job
5. verify `pipeline_runs`, raw responses, and gold rows
6. confirm any remaining Parquet dependency is intentional
7. treat PostgreSQL as the primary runtime source of truth

### Cutover checkpoints

Before declaring cutover complete, confirm:

- migrations are at the expected revision
- cities were seeded successfully
- at least one successful `pipeline_runs` row exists after cutover
- raw responses are written or reused correctly
- gold rows are present and deduplicated
- logs reflect DB-backed completion rather than file-backed success
- any dashboard or downstream Parquet dependency is known and explicitly temporary

## Rollback guidance

If the PostgreSQL-first path fails in a shared environment:

1. stop relying on the failed DB-first run output
2. inspect the latest `pipeline_runs` row and logs
3. confirm whether the failure happened in:
   - migration/bootstrap
   - city seed
   - extract
   - gold load
4. correct the issue
5. rerun verification from the beginning

If a temporary compatibility rollback is necessary:

- re-enable `WRITE_GOLD_PARQUET=1` only if a downstream consumer still needs a file artifact
- keep PostgreSQL as the authoritative operational data store if the DB writes succeeded
- avoid reverting schema versions in shared environments unless the failure clearly requires it

## Known temporary limitations

- the pipeline is PostgreSQL-first
- the Streamlit dashboard still reads Parquet
- Parquet is a secondary compatibility artifact, not the primary gold-data contract
- cutover is not fully complete for the user-facing app until the dashboard reads PostgreSQL directly
