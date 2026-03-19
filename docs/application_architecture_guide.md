# City Air Tracker Application Architecture Guide

## Audience and purpose

This document explains how the City Air Tracker application is structured, why it is built this way, and what its main terms mean. It is written for programmers who may be comfortable with web applications or scripts but are new to data pipelines.

The guide is based on the code in the repository, not only on the existing diagrams. Where the implementation is a proof of concept, that is called out directly.

## What this application does

City Air Tracker is a small batch data pipeline plus a read-only dashboard.

At a high level, the application:

1. Reads a list of cities from `configs/cities.csv`.
2. Converts each city into latitude and longitude using the OpenWeather geocoding API.
3. Downloads historical air-pollution measurements for each city from OpenWeather.
4. Stores the API responses as raw JSON files.
5. Transforms those raw files into a cleaner analytical dataset in Parquet format.
6. Optionally publishes the same data to PostgreSQL.
7. Displays the final dataset in a Streamlit dashboard.

This is an ETL-style workflow:

- Extract means reading data from external systems.
- Transform means reshaping and enriching that data.
- Load means writing the prepared result to storage for later use.

## Big-picture architecture

The repository contains two main runtime services and a shared set of files:

- `services/pipeline`: the batch job that collects and prepares air-quality data.
- `services/dashboard`: the Streamlit application that reads the prepared dataset.
- `configs`: input configuration such as the city list.
- `data/raw`: cached API responses and manifests.
- `data/gold`: the final analytical dataset used by the dashboard.
- `docs`: diagrams and supporting documentation.

The architecture intentionally separates data collection from data presentation. The dashboard does not call external APIs directly. Instead, it only reads the already prepared gold dataset.

That separation keeps the dashboard simple and makes the pipeline the single place where API access, caching, and normalization happen.

## Main execution flow

The entry point for the pipeline is `services/pipeline/run_pipeline.py`.

When the pipeline starts, it does the following:

1. Reads runtime settings from the configuration layer.
2. Creates the raw and gold output directories if they do not exist.
3. Computes a time window ending at the current UTC time.
4. Loads the list of configured cities.
5. Loops through each city and runs the extract phase.
6. Passes the collected raw files into the transform phase.
7. Writes the final dataset in the load phase.

This means the pipeline is orchestrated by one simple command-line program rather than by a workflow engine such as Airflow or Prefect. For a proof of concept, that is a practical choice because the control flow is easy to follow and debug.

In Docker Compose development, the pipeline still runs from that same CLI entrypoint, but the stack now also includes Azure-compatible local storage emulator support to prepare for future storage work without changing the basic execution model.

## Pipeline layers

## Input configuration

The pipeline begins with `services/pipeline/src/pipeline/extract/cities.py`.

`read_cities()` reads `configs/cities.csv` into a `CitySpec` data class with:

- `city`
- `country_code`
- optional `state`

This is the first design decision worth noticing: cities are treated as configuration, not as database records. That keeps the pipeline easy to run locally and easy to understand. The tradeoff is that changing the city list requires editing a file instead of updating an admin screen.

## Extract layer

The extract layer is split into small modules:

- `geocoding.py`
- `openweather_air_pollution.py`
- `http.py`

### Geocoding

`geocode_city()` takes a city, country code, and optional state, then calls the OpenWeather direct geocoding API.

Before making the API call, it checks whether a cached geocoding file already exists in:

- `data/raw/openweather/geocoding`

If a cached file exists, the pipeline reuses it. If not, it calls the API and writes a JSON cache file.

This is an important pipeline idea: raw data is often stored even when it looks redundant. Caching raw responses makes reruns faster and gives a record of what the external system returned.

### Air pollution history

`fetch_air_pollution_history()` calls the OpenWeather historical air-pollution endpoint for one city and one time window.

For each run, the function:

- builds a deterministic `geo_id` from city, country code, latitude, and longitude
- creates a city-specific directory under `data/raw/openweather/air_pollution/history`
- writes the API response to a timestamped JSON file
- writes a manifest file to `data/raw/openweather/_manifests`

The manifest is small metadata about the extract step, such as run id, request window, status code, record count, and output path. This is a common pipeline pattern because it provides lightweight traceability without requiring a separate metadata service.

### HTTP behavior

`http.py` contains two pieces of cross-cutting infrastructure:

- `RateLimiter`, which spaces requests based on a configured maximum calls per minute
- `get_with_retries()`, which retries transient failures and handles HTTP 429 backoff

This logic is centralized instead of being repeated in each extractor. That keeps API access rules consistent and makes the extractor modules easier to read.

## Transform layer

The main transform code is in `services/pipeline/src/pipeline/transform/openweather_air_pollution_transform.py`.

`build_gold_from_raw()` reads every raw JSON file produced by the extract layer and converts them into a single pandas DataFrame.

For each measurement row, the transform creates:

- event time as `ts`
- location fields such as `city`, `country_code`, `lat`, `lon`, and `geo_id`
- the OpenWeather AQI value
- pollution component measurements such as `pm2_5`, `pm10`, `o3`, and `no2`

After parsing, the transform:

- converts timestamps to UTC-aware pandas timestamps
- sorts rows by city and time
- removes duplicates by `geo_id` and `ts`
- computes a 24-sample rolling average for `pm2_5`
- adds a human-readable AQI category
- adds a derived risk score

The transform code assumes the OpenWeather history endpoint returns hourly observations, so a 24-row rolling window represents about 24 hours. This is a convenient proof-of-concept assumption, but it would need stronger validation in a production pipeline.

### Derived fields

`risk_scoring.py` adds two fields:

- `aqi_category`: maps numeric AQI values 1 through 5 into labels such as Good or Very Poor
- `risk_score`: a simple weighted formula that combines AQI and selected pollutant values

The risk score is explicitly rule-based and simple. That is a design choice in favor of readability over scientific sophistication. It gives the dashboard a single sortable metric without introducing a machine-learning dependency or complex domain logic.

## Load layer

The load code lives in `services/pipeline/src/pipeline/load/storage.py`.

`publish_outputs()` writes the transformed DataFrame to the local gold parquet path and can also publish the same DataFrame to PostgreSQL when enabled.

Examples:
- local: `data/gold/air_pollution_gold.parquet`

If `use_postgres` is enabled in the settings, it also writes the same DataFrame to a PostgreSQL table using `to_sql(..., if_exists="replace")`.

This reveals another major design decision:

- Parquet is the default source of truth for analytics and dashboard reads.
- PostgreSQL is optional and behaves more like a publishing target than the primary storage layer.

For a small local pipeline, Parquet is a good fit because it is compact, columnar, and easy for pandas to read. The tradeoff is that file-based outputs are less convenient than a database when many concurrent readers or incremental updates are needed.

## Dashboard architecture

The dashboard code is in `services/dashboard/app`.

The dashboard has one home page and two analysis pages:

- `Home.py`
- `pages/1_City_Trends.py`
- `pages/2_Compare_Cities.py`

All pages read the gold Parquet dataset directly. The dashboard does not perform additional extraction or transformation beyond lightweight filtering and plotting.

### Home page

The home page:

- checks whether the gold dataset exists
- loads the Parquet file into pandas
- displays simple summary metrics
- shows a preview table

### City Trends page

The trends page:

- lets the user choose one `geo_id`
- lets the user choose one metric
- plots that metric over time with Plotly
- shows recent rows for that city

### Compare Cities page

The comparison page:

- computes the latest row for each city
- lets the user choose one metric
- plots the latest value per city
- displays the same values in a table

This dashboard is intentionally thin. Most data systems become easier to maintain when expensive or reusable logic stays in the pipeline, while the dashboard acts mainly as a reader of prepared data.

## Data storage model

The application uses a layered storage approach that is common in analytics work:

- Config layer: `configs/cities.csv`
- Raw layer: JSON responses and manifests under `data/raw`
- Gold layer: curated Parquet dataset under `data/gold`
- Optional serving layer: PostgreSQL table for downstream consumers

For programmers who are new to pipelines, the main idea is that each layer has a different purpose.

- The config layer defines what to collect.
- The raw layer preserves original external responses.
- The gold layer is cleaned, structured, and ready for analysis.
- The serving layer is optional and exists to make consumption easier for other tools.

## Runtime and deployment model

The repository can run either locally in a Python virtual environment or through Docker Compose.

`docker-compose.yml` defines five services:

- `pipeline`
- `dashboard`
- `postgres`
- `adminer`
- `azurite`

The pipeline container writes to the shared `data` volume, and the dashboard container reads from that same output. This means Docker Compose preserves the same architectural separation found in local development.

The `azurite` service provides an Azure-compatible blob emulator for local development. At the moment, that emulator support is runtime scaffolding; the pipeline's actual gold dataset still lands in the shared local parquet path unless a future storage change updates the load implementation.

One subtle implementation detail is that the settings defaults point to `/app/...` paths. Those defaults match the container layout. Local execution works best when environment variables or compatible paths are provided.

For more detail on the emulator-oriented Docker setup, see `docs/docker_compose_azure_local_dev.md`.

## Design decisions and why they matter

### 1. Batch processing instead of streaming

The application runs as a batch job over a recent history window. It does not continuously ingest events.

Why this helps:

- simpler control flow
- easy local execution
- easy reruns for a fixed time window

Tradeoff:

- data is only as fresh as the most recent pipeline run

### 2. File-backed raw cache

Both geocoding responses and pollution responses are written to disk.

Why this helps:

- reduces repeated API calls
- supports debugging
- preserves source responses for later inspection

Tradeoff:

- cache invalidation is manual
- reruns with changed semantics may reuse older raw files

### 3. Clear extract/transform/load separation

The modules are organized by pipeline stage instead of by API endpoint alone.

Why this helps:

- the code mirrors the mental model used in data engineering
- each layer has a focused responsibility
- testing can target one stage at a time

Tradeoff:

- some developers may need a short introduction to ETL vocabulary

### 4. Parquet-first analytics storage

The gold dataset is always written in Parquet format, and the current implementation writes that file to the local gold directory.

Why this helps:

- efficient for tabular analytics
- straightforward with pandas
- easy for the dashboard to consume

Tradeoff:

- not optimized for transactional updates
- less discoverable than a database for some users

The repository now also includes Azure-compatible local development settings and an Azurite container in Docker Compose, but those settings are currently scaffolding for local development rather than an active Azure-backed gold output path.

### 5. Optional PostgreSQL publishing

Database loading is controlled by configuration and is not required for the dashboard.

Why this helps:

- keeps the default path simple
- allows future downstream integrations

Tradeoff:

- two output paths must stay conceptually aligned when PostgreSQL is enabled

### 6. Thin dashboard, heavier pipeline

The dashboard reads prepared data rather than reproducing transformation logic.

Why this helps:

- one place for business rules
- simpler UI code
- fewer surprises between analysis pages

Tradeoff:

- dashboard behavior depends on pipeline freshness and schema stability

## Terminology guide

### Batch job

A program that runs, processes a bounded amount of data, and exits.

In this repository, the pipeline command is a batch job.

### Pipeline

A sequence of steps that moves data from source systems to a prepared output.

Here, the steps are city input, geocoding, API extraction, transformation, and load.

### Raw data

Data stored close to the original source response, usually with minimal cleanup.

In this application, raw data is JSON saved under `data/raw`.

### Gold dataset

A cleaned and analysis-ready dataset intended for direct use by reports, dashboards, or analysts.

Here, the gold dataset is `air_pollution_gold.parquet`.

### Manifest

A metadata file that records what a pipeline run fetched or wrote.

Here, manifests capture request windows, record counts, and paths to raw files.

### Orchestration

The logic that decides what order the pipeline steps run in.

Here, orchestration is handled by `run_pipeline.py`.

### Idempotence

The idea that rerunning a job should not create inconsistent results.

This pipeline is partly idempotent because it reuses cached files for the same output path, but it is not a fully managed idempotent system with versioned datasets or partition replacement.

### Schema

The set of columns and types in a dataset.

The schema of the gold dataset is defined by the transform code rather than by a separate schema registry.

## Implementation details that shape behavior

Several code-level details are important for understanding how the application behaves:

- `run_id` is generated once per pipeline run and becomes part of raw output filenames.
- `geo_id` combines city, country code, latitude, and longitude to create a stable location key.
- transform logic infers city metadata from the raw file path instead of re-reading a manifest.
- duplicate handling keeps the last row for each `geo_id` and timestamp combination.
- PostgreSQL writes replace the whole target table instead of performing incremental upserts.
- the included test coverage currently focuses on transform parsing, not end-to-end pipeline execution.

These choices are reasonable for a proof of concept because they keep the code approachable. They also identify likely extension points if the application grows.

## Practical limitations

This repository is intentionally simple, so a few limitations are part of the current architecture:

- There is no workflow scheduler in the repo.
- There is no formal schema validation on raw API payloads.
- There is no incremental partitioning strategy for the gold dataset.
- There is no history-aware cache invalidation policy.
- There is no domain-specific explanation of whether the derived risk score is scientifically calibrated.

None of those limitations make the project unclear. They simply show that the application is designed as a learning-oriented pipeline and dashboard rather than as a full production platform.

## Summary

City Air Tracker is a compact example of a layered data application.

Its architecture is centered on a simple idea:

- collect external air-quality data in a reproducible batch process
- preserve source responses in a raw layer
- transform them into one clean analytical dataset
- let the dashboard read that prepared dataset directly

For programmers who are new to pipelines, the most useful mental model is that this application is not a dashboard that happens to fetch data. It is a pipeline-first system where the dashboard is the final consumer of a curated dataset.
