# PostgreSQL Migrations Guide

This guide explains the migration and bootstrap workflow introduced for `AIR-012.2`.

## Migration tool

This project uses Alembic for PostgreSQL schema versioning.

Alembic is configured at the repository root:

- `alembic.ini`
- `migrations/env.py`
- `migrations/versions/`

## Database URL resolution

Alembic resolves the target database in this order:

1. `ALEMBIC_DATABASE_URL`, if set
2. the PostgreSQL connection values already defined in `.env`

That means the normal application settings can drive migrations without adding a second required database configuration path.

## Local bootstrap

To create or upgrade the schema locally:

```bash
alembic upgrade head
```

To inspect the current migration state:

```bash
alembic current
```

To view migration history:

```bash
alembic history
```

## Docker Compose bootstrap

The repository includes a dedicated `migrate` service:

```bash
docker compose run --rm migrate
```

That service runs:

```bash
alembic upgrade head
```

The pipeline service depends on the migration service so schema bootstrap can happen before pipeline execution.

## Baseline schema

The baseline migration creates:

- `cities`
- `geocoding_cache`
- `pipeline_runs`
- `raw_air_pollution_responses`
- `air_pollution_gold`

These tables match the schema design in `docs/architecture/postgresql_schema_design.md`.

## Fresh-database validation

The expected bootstrap validation flow is:

1. start PostgreSQL
2. run `alembic upgrade head`
3. seed cities with `python -m pipeline.cli --seed-cities`
4. run the pipeline and verify `air_pollution_gold` is populated in PostgreSQL
5. verify the migration completes without error
6. verify the expected tables exist

Example table check:

```bash
psql postgresql://cityair:cityair@localhost:5432/cityair -c "\\dt"
```

Example gold-row check:

```bash
psql postgresql://cityair:cityair@localhost:5432/cityair -c "select count(*) from air_pollution_gold;"
```

## Notes

- The baseline migration is the first schema version for the PostgreSQL-first MVP.
- Normal pipeline runs now expect PostgreSQL to be the primary gold-data target.
- Later schema changes should be added as new Alembic revision files rather than editing the baseline migration after it has been applied in shared environments.
