# PostgreSQL Schema Design (AIR-012.7)

## Purpose

This document defines the PostgreSQL schema for the City Air Tracker MVP migration from a file-based pipeline to a DB-first pipeline.

On the current `main` branch, the system relies on:

- `configs/cities.csv` for city configuration
- `data/raw/openweather/geocoding/*.json` for geocoding cache
- `data/raw/openweather/air_pollution/history/.../*.json` for raw extract payloads
- `data/raw/openweather/_manifests/*.json` for extract metadata
- `data/gold/air_pollution_gold.parquet` for the analytical dataset

The MVP target state replaces those runtime contracts with PostgreSQL as the primary system of record for:

- city configuration
- geocoding cache
- raw ingestion history
- pipeline run tracking
- gold analytical data

This document covers the logical schema and data-contract decisions for that migration.

## Design Goals

- Make PostgreSQL the primary runtime store for the pipeline MVP
- Preserve the current business output used by the app
- Support repeatable reruns without uncontrolled duplication
- Keep the schema understandable for maintainers who are new to ETL systems
- Separate configuration, raw ingestion, operational metadata, and analytical output
- Support future incremental loading without requiring a full-table replace on every run

## Non-Goals

- This document does not define migration-tool syntax
- This document does not define dashboard query shapes in detail
- This document does not optimize for multiple interchangeable storage backends
- This document does not preserve file-path-based runtime behavior as a primary contract

## Current-to-Target Mapping

| Current artifact | Current role | PostgreSQL replacement |
|---|---|---|
| `configs/cities.csv` | input city list | `cities` |
| geocoding JSON cache | cached coordinates | `geocoding_cache` |
| raw air pollution JSON files | raw extracted payloads | `raw_air_pollution_responses` |
| raw manifest JSON files | request and ingestion metadata | `raw_air_pollution_responses` plus `pipeline_runs` |
| parquet gold dataset | analytical output | `air_pollution_gold` |
| implicit runtime state in logs and file names | run tracking | `pipeline_runs` |

## Schema Overview

The MVP schema contains five main tables:

1. `cities`
2. `geocoding_cache`
3. `pipeline_runs`
4. `raw_air_pollution_responses`
5. `air_pollution_gold`

Recommended schema name:

- `public` for the MVP

## Table Design

### 1. `cities`

Purpose:

- replace `configs/cities.csv` as the source of truth for which cities the pipeline processes

Columns:

| Column | Type | Null | Notes |
|---|---|---:|---|
| `id` | bigint | no | surrogate primary key |
| `city` | text | no | normalized display name used in pipeline configuration |
| `country_code` | text | no | ISO country code |
| `state` | text | yes | optional state or region |
| `is_active` | boolean | no | default `true`; inactive rows are ignored by the pipeline |
| `created_at` | timestamptz | no | row creation time |
| `updated_at` | timestamptz | no | last update time |

Primary key:

- `id`

Uniqueness:

- unique on `(city, country_code, coalesce(state, ''))`

Notes:

- This mirrors the current CSV contract closely so migration is simple.
- `is_active` allows cities to be disabled without deleting them.

### 2. `geocoding_cache`

Purpose:

- replace JSON geocoding cache files with durable cached coordinates

Columns:

| Column | Type | Null | Notes |
|---|---|---:|---|
| `id` | bigint | no | surrogate primary key |
| `city_id` | bigint | no | foreign key to `cities.id` |
| `query_text` | text | no | exact query sent to OpenWeather |
| `lat` | numeric(9,6) | no | cached latitude |
| `lon` | numeric(9,6) | no | cached longitude |
| `provider_name` | text | yes | geocoder returned place name |
| `provider_state` | text | yes | geocoder returned state |
| `provider_country` | text | yes | geocoder returned country |
| `fetched_at` | timestamptz | no | when the geocoding result was retrieved |
| `created_at` | timestamptz | no | row creation time |

Primary key:

- `id`

Foreign keys:

- `city_id` -> `cities.id`

Uniqueness:

- unique on `city_id`

Notes:

- The current implementation chooses the first geocoding result deterministically; this table stores the selected result only.
- For the MVP, one active cached coordinate set per city is enough.

### 3. `pipeline_runs`

Purpose:

- persist operational metadata for every pipeline execution

Columns:

| Column | Type | Null | Notes |
|---|---|---:|---|
| `id` | bigint | no | surrogate primary key |
| `run_id` | text | no | externally visible run identifier; matches pipeline logs |
| `source` | text | no | current value is expected to be `openweather` |
| `history_hours` | integer | no | configured runtime window width |
| `window_start_utc` | timestamptz | no | extract window start |
| `window_end_utc` | timestamptz | no | extract window end |
| `status` | text | no | expected values: `running`, `succeeded`, `failed` |
| `city_count` | integer | yes | number of target cities for the run |
| `raw_response_count` | integer | yes | count of raw response rows created or reused |
| `gold_row_count` | integer | yes | count of gold rows inserted or updated |
| `error_message` | text | yes | failure summary if the run fails |
| `started_at` | timestamptz | no | run start time |
| `finished_at` | timestamptz | yes | run end time |
| `created_at` | timestamptz | no | row creation time |

Primary key:

- `id`

Uniqueness:

- unique on `run_id`

Notes:

- This table replaces the implicit run metadata currently encoded in filenames and logs.
- `run_id` should remain human-readable and stable for tracing.

### 4. `raw_air_pollution_responses`

Purpose:

- replace raw history JSON files and manifest JSON files
- store request metadata, provider response payload, and ingestion identity

Columns:

| Column | Type | Null | Notes |
|---|---|---:|---|
| `id` | bigint | no | surrogate primary key |
| `pipeline_run_id` | bigint | no | foreign key to `pipeline_runs.id` |
| `city_id` | bigint | no | foreign key to `cities.id` |
| `geo_id` | text | no | deterministic geo key matching current pipeline semantics |
| `lat` | numeric(9,6) | no | coordinates used for the request |
| `lon` | numeric(9,6) | no | coordinates used for the request |
| `request_url` | text | no | request endpoint |
| `request_start_utc` | timestamptz | no | requested historical window start |
| `request_end_utc` | timestamptz | no | requested historical window end |
| `status_code` | integer | no | HTTP response status |
| `record_count` | integer | no | number of records inside provider payload |
| `payload_json` | jsonb | no | raw provider response body |
| `fetched_at` | timestamptz | no | when the response was retrieved |
| `created_at` | timestamptz | no | row creation time |

Primary key:

- `id`

Foreign keys:

- `pipeline_run_id` -> `pipeline_runs.id`
- `city_id` -> `cities.id`

Uniqueness:

- unique on `(city_id, request_start_utc, request_end_utc)`

Notes:

- This uniqueness rule is the MVP idempotency contract for raw historical ingestion.
- `payload_json` keeps the raw provider response intact for replay and audit.
- `geo_id` is stored as a materialized value because the current transform and dashboard semantics rely on it.

### 5. `air_pollution_gold`

Purpose:

- store the curated analytical dataset currently written to Parquet

Columns:

| Column | Type | Null | Notes |
|---|---|---:|---|
| `id` | bigint | no | surrogate primary key |
| `pipeline_run_id` | bigint | no | foreign key to `pipeline_runs.id` |
| `raw_response_id` | bigint | yes | optional lineage link to raw response row |
| `city_id` | bigint | no | foreign key to `cities.id` |
| `ts` | timestamptz | no | observation timestamp in UTC |
| `city` | text | no | denormalized for easy reads and parity with current output |
| `country_code` | text | no | denormalized for easy reads |
| `lat` | numeric(9,6) | no | observation coordinate |
| `lon` | numeric(9,6) | no | observation coordinate |
| `geo_id` | text | no | deterministic location key |
| `aqi` | integer | yes | OpenWeather AQI value |
| `co` | numeric(12,4) | yes | component value |
| `no` | numeric(12,4) | yes | component value |
| `no2` | numeric(12,4) | yes | component value |
| `o3` | numeric(12,4) | yes | component value |
| `so2` | numeric(12,4) | yes | component value |
| `nh3` | numeric(12,4) | yes | component value |
| `pm2_5` | numeric(12,4) | yes | component value |
| `pm10` | numeric(12,4) | yes | component value |
| `pm2_5_24h_avg` | numeric(12,4) | yes | derived rolling average |
| `aqi_category` | text | no | derived category |
| `risk_score` | numeric(12,4) | yes | derived risk score |
| `created_at` | timestamptz | no | row creation time |
| `updated_at` | timestamptz | no | row update time |

Primary key:

- `id`

Foreign keys:

- `pipeline_run_id` -> `pipeline_runs.id`
- `raw_response_id` -> `raw_air_pollution_responses.id`
- `city_id` -> `cities.id`

Uniqueness:

- unique on `(geo_id, ts)`

Notes:

- The unique key on `(geo_id, ts)` matches the current dedupe behavior in pandas.
- This table is the PostgreSQL replacement for `air_pollution_gold.parquet`.
- Denormalized city fields are intentional for simple analytics and dashboard reads.

## Relationship Summary

- one `cities` row may have zero or one active `geocoding_cache` row
- one `pipeline_runs` row may have many `raw_air_pollution_responses`
- one `cities` row may have many `raw_air_pollution_responses`
- one `pipeline_runs` row may have many `air_pollution_gold` rows
- one `cities` row may have many `air_pollution_gold` rows
- one `raw_air_pollution_responses` row may contribute many `air_pollution_gold` rows

## Derived Values and Storage Decisions

The MVP stores some derived values directly in the gold table instead of recomputing them on every read:

- `geo_id`
- `pm2_5_24h_avg`
- `aqi_category`
- `risk_score`

Reason:

- this preserves parity with the current pipeline output
- it keeps the dashboard and downstream reads simple
- it makes the first DB-backed MVP easier to validate against the existing Parquet dataset

## Idempotency and Deduplication Rules

### Cities

- city identity is unique on `(city, country_code, state)`

### Geocoding cache

- one cached coordinate row per city
- refreshing the cache should update the existing row instead of creating duplicates

### Raw responses

- one logical raw ingestion per city and requested time window
- rerunning the same city/window should reuse or upsert the same logical raw row

### Gold rows

- one gold record per `(geo_id, ts)`
- reruns should upsert rather than append duplicates

## Index Recommendations

These are logical index requirements for the MVP. Exact migration syntax belongs in the next ticket.

- `cities`: unique index on `(city, country_code, coalesce(state, ''))`
- `geocoding_cache`: unique index on `city_id`
- `pipeline_runs`: unique index on `run_id`
- `raw_air_pollution_responses`: unique index on `(city_id, request_start_utc, request_end_utc)`
- `raw_air_pollution_responses`: index on `pipeline_run_id`
- `air_pollution_gold`: unique index on `(geo_id, ts)`
- `air_pollution_gold`: index on `city_id`
- `air_pollution_gold`: index on `ts`

## Operational Assumptions

- The source remains OpenWeather for the MVP.
- Pipeline runs remain batch-oriented.
- Historical fetches still use a configurable `history_hours` window.
- PostgreSQL is the primary runtime store; file artifacts may exist temporarily during migration, but they are no longer the target contract.

## Open Questions

These should be resolved before or during implementation, but they do not block the schema draft itself.

1. Should `geocoding_cache` keep history, or is one current row per city enough for the MVP?
2. Should `raw_air_pollution_responses` store a payload checksum to detect provider changes for the same requested window?
3. Should `air_pollution_gold` keep `raw_response_id` mandatory, or allow null during backfill/import scenarios?
4. Should future retention rules archive old raw payloads, or is full retention acceptable for the MVP?

## Recommended Follow-On Tickets

- `AIR-012.8` Add repeatable database migrations and schema bootstrap
- `AIR-012.9` Create cities table and seed/import flow from the current city CSV
- `AIR-012.10` Persist geocoding cache in PostgreSQL
- `AIR-012.11` Persist raw OpenWeather responses and extract metadata in PostgreSQL
- `AIR-012.12` Add pipeline run tracking and status persistence
- `AIR-012.13` Refactor transform stage to build gold data from PostgreSQL raw records
- `AIR-012.14` Add keys and upsert rules for the gold air pollution table
