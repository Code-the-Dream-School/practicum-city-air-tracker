# Function Call Flows

This document describes the current function-level runtime flows on `main`.
It is meant to answer: "when I run the app, which functions call which other functions, and in what order?"

## Scope

The diagrams below cover:

- pipeline CLI entrypoint
- scheduler-compatible entrypoint
- city seeding flow
- pipeline run orchestration
- geocoding cache hit and miss behavior
- raw air-pollution extract cache hit and miss behavior
- transform flow
- load flow
- dashboard frontend to backend flow

## 1. Pipeline CLI Run Flow

Source files:

- `services/pipeline/run_pipeline.py`
- `services/pipeline/src/pipeline/cli.py`
- `services/pipeline/src/pipeline/orchestration/__init__.py`

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Entry as run_pipeline.py
    participant CLI as pipeline.cli.main
    participant Orch as orchestration.run_pipeline_job
    participant Track as run_tracking
    participant Extract as run_extract_stage
    participant Transform as run_transform_stage
    participant Load as run_load_stage

    User->>Entry: python -m pipeline.cli --history-hours 72
    Entry->>CLI: main()
    CLI->>CLI: argparse.ArgumentParser(...)
    CLI->>Orch: run_pipeline_job(source, history_hours)
    Orch->>Orch: ensure_output_directories()
    Orch->>Orch: build_runtime_window(history_hours)
    Orch->>Track: create_pipeline_run(...)
    Orch->>Extract: run_extract_stage(raw_dir, start, end, run_id, pipeline_run_id)
    Extract-->>Orch: raw_records, city_count
    Orch->>Transform: run_transform_stage(raw_records)
    Transform-->>Orch: gold_df
    Orch->>Load: run_load_stage(gold_df, gold_dir)
    Load-->>Orch: PublishResult
    Orch->>Track: update_pipeline_run_status(... succeeded ...)
    Orch-->>CLI: PipelineRunResult
```

## 1.1 Scheduler-Compatible Run Flow

Source file:

- `services/pipeline/src/pipeline/orchestration/scheduler.py`

```mermaid
sequenceDiagram
    autonumber
    actor Scheduler
    participant Sched as orchestration.scheduler.run_pipeline_job
    participant Orch as orchestration.run_pipeline_job

    Scheduler->>Sched: run_pipeline_job(source, history_hours)
    Sched->>Orch: run_pipeline_job(source, history_hours)
    Orch-->>Sched: PipelineRunResult
```

Note:

- `scheduler.py` is a temporary compatibility wrapper; Prefect is now the active orchestration direction.
- Recurring job registration and cadence configuration are follow-up capabilities to be implemented via Prefect deployments.

## 2. Seed Cities Flow

This flow runs when the CLI is invoked with `--seed-cities`.

Source file:

- `services/pipeline/src/pipeline/extract/cities.py`

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant CLI as pipeline.cli.main
    participant Cities as extract.cities.seed_cities_from_file
    participant File as cities.csv
    participant DB as PostgreSQL cities

    User->>CLI: python -m pipeline.cli --seed-cities
    CLI->>Cities: seed_cities_from_file(settings.cities_file)
    Cities->>Cities: _validate_cities_file(path)
    Cities->>File: pd.read_csv(path)
    Cities->>Cities: _parse_cities_dataframe(df)
    Cities->>Cities: _build_postgres_engine()
    Cities->>DB: SELECT city, country_code, state FROM cities
    loop per parsed city
        Cities->>DB: INSERT INTO cities (...) when not already present
    end
    Cities-->>CLI: CitySeedResult
```

## 3. Extract Stage Flow

The extract stage is coordinated by `run_extract_stage()` and loops through each active city.

```mermaid
sequenceDiagram
    autonumber
    participant Orch as orchestration.run_extract_stage
    participant Cities as extract.cities.read_cities
    participant Geo as extract.geocoding.geocode_city
    participant Air as extract.openweather_air_pollution.fetch_air_pollution_history

    Orch->>Cities: read_cities(cities_path)
    Cities-->>Orch: list[CitySpec]
    loop per city
        Orch->>Geo: geocode_city(raw_dir, city, country_code, state)
        Geo-->>Orch: Coords
        Orch->>Air: fetch_air_pollution_history(raw_dir, city, country_code, lat, lon, start, end, run_id, pipeline_run_id)
        Air-->>Orch: RawAirPollutionRecord
    end
    Orch-->>Orch: return raw_records, len(cities)
```

## 4. Geocoding Flow

### 4.1 Cache Hit

```mermaid
sequenceDiagram
    autonumber
    participant Orch as run_extract_stage
    participant Geo as geocode_city
    participant DB as PostgreSQL

    Orch->>Geo: geocode_city(...)
    Geo->>Geo: _build_postgres_engine()
    Geo->>DB: _lookup_city_id(...)
    Geo->>DB: _read_cached_coords(city_id)
    DB-->>Geo: lat, lon
    Geo-->>Orch: Coords
```

### 4.2 Cache Miss

```mermaid
sequenceDiagram
    autonumber
    participant Orch as run_extract_stage
    participant Geo as geocode_city
    participant HTTP as get_with_retries
    participant API as OpenWeather Geocoding API
    participant DB as PostgreSQL

    Orch->>Geo: geocode_city(...)
    Geo->>Geo: _build_postgres_engine()
    Geo->>DB: _lookup_city_id(...)
    Geo->>DB: _read_cached_coords(city_id)
    DB-->>Geo: no row
    Geo->>Geo: _limiter.wait()
    Geo->>HTTP: get_with_retries(GEO_URL, params)
    HTTP->>API: GET /geo/1.0/direct
    API-->>HTTP: JSON array
    HTTP-->>Geo: response
    Geo->>Geo: choose arr[0]
    Geo->>DB: _lookup_city_id(...) again
    Geo->>DB: _upsert_geocoding_cache(...)
    Geo-->>Orch: Coords
```

## 5. Raw Air-Pollution Extract Flow

### 5.1 Existing Raw Response Reused

```mermaid
sequenceDiagram
    autonumber
    participant Orch as run_extract_stage
    participant Air as fetch_air_pollution_history
    participant DB as PostgreSQL

    Orch->>Air: fetch_air_pollution_history(...)
    Air->>Air: _geo_id(city, country_code, lat, lon)
    Air->>Air: _build_postgres_engine()
    Air->>DB: _lookup_city_id(city, country_code)
    Air->>DB: _find_existing_raw_response(city_id, start, end)
    DB-->>Air: existing row
    Air->>Air: _build_record(row, city, country_code, payload_json)
    Air-->>Orch: RawAirPollutionRecord
```

### 5.2 New Raw Response Inserted

```mermaid
sequenceDiagram
    autonumber
    participant Orch as run_extract_stage
    participant Air as fetch_air_pollution_history
    participant HTTP as get_with_retries
    participant API as OpenWeather Air Pollution API
    participant DB as PostgreSQL

    Orch->>Air: fetch_air_pollution_history(...)
    Air->>Air: _geo_id(...)
    Air->>Air: _build_postgres_engine()
    Air->>DB: _lookup_city_id(...)
    Air->>DB: _find_existing_raw_response(city_id, start, end)
    DB-->>Air: no row
    Air->>Air: _limiter.wait()
    Air->>HTTP: get_with_retries(AIR_URL, params)
    HTTP->>API: GET /data/2.5/air_pollution/history
    API-->>HTTP: JSON payload
    HTTP-->>Air: response
    Air->>DB: INSERT INTO raw_air_pollution_responses
    Air->>DB: SELECT inserted row when needed
    Air->>Air: _build_record(row, city, country_code, data)
    Air-->>Orch: RawAirPollutionRecord
```

## 6. Transform Flow

The transform stage does not read from PostgreSQL directly.
It receives `list[RawAirPollutionRecord]` from orchestration and builds a DataFrame in memory.

Source files:

- `services/pipeline/src/pipeline/transform/openweather_air_pollution_transform.py`
- `services/pipeline/src/pipeline/transform/risk_scoring.py`

```mermaid
sequenceDiagram
    autonumber
    participant Orch as orchestration.run_transform_stage
    participant Transform as build_gold_from_raw_records
    participant AQI as add_aqi_category
    participant Risk as add_risk_score

    Orch->>Transform: build_gold_from_raw_records(raw_records)
    loop per RawAirPollutionRecord
        loop per payload_json.list item
            Transform->>Transform: build row dict
        end
    end
    Transform->>Transform: pd.DataFrame(rows)
    Transform->>Transform: pd.to_datetime(df["ts"], utc=True)
    Transform->>Transform: sort_values(...).drop_duplicates(...)
    Transform->>Transform: groupby("geo_id").rolling(...).mean()
    Transform->>AQI: add_aqi_category(df)
    AQI-->>Transform: df with aqi_category
    Transform->>Risk: add_risk_score(df)
    Risk-->>Transform: df with risk_score
    Transform-->>Orch: gold_df
```

## 7. Load Flow

The load stage is the point where the in-memory DataFrame is persisted again.

```mermaid
sequenceDiagram
    autonumber
    participant Orch as orchestration.run_load_stage
    participant Storage as load.storage.publish_outputs
    participant DB as PostgreSQL air_pollution_gold
    participant File as gold parquet file
    participant Blob as Azure Blob / Azurite

    Orch->>Storage: publish_outputs(gold_df, gold_dir, "air_pollution_gold")
    alt settings.use_postgres is true
        Storage->>Storage: _build_postgres_engine()
        Storage->>Storage: _upsert_gold_rows(engine, gold_df, table_name)
        Storage->>Storage: _prepare_gold_rows(gold_df)
        Storage->>Storage: _build_gold_upsert_statement(table_name, rows)
        Storage->>DB: INSERT ... ON CONFLICT (geo_id, ts) DO UPDATE
    end
    alt settings.write_gold_parquet is true
        Storage->>File: gold_df.to_parquet(...)
    end
    alt settings.write_gold_azure_blob is true
        Storage->>Storage: _resolve_azure_blob_path(table_name)
        Storage->>Storage: _upload_gold_to_azure_blob(gold_df, table_name)
        Storage->>Blob: create container if needed + upload blob
    end
    Storage-->>Orch: PublishResult
```

## 8. Pipeline Success and Failure Status Updates

```mermaid
sequenceDiagram
    autonumber
    participant Orch as run_pipeline_job
    participant Track as run_tracking

    Orch->>Track: create_pipeline_run(...)
    alt all stages succeed
        Orch->>Track: update_pipeline_run_status(status="succeeded", city_count, raw_response_count, gold_row_count, finished_at)
    else any stage raises exception
        Orch->>Track: update_pipeline_run_status(status="failed", city_count?, raw_response_count?, error_message, finished_at)
        Orch-->>Orch: re-raise exception
    end
```

## 9. Dashboard Frontend Load Flow

Source files:

- `services/dashboard/frontend/src/main.jsx`
- `services/dashboard/frontend/src/App.jsx`
- `services/dashboard/frontend/src/hooks/useDashboardViewModel.js`
- `services/dashboard/frontend/src/hooks/useDashboardData.js`
- `services/dashboard/frontend/src/hooks/useLocalStorageState.js`

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Main as frontend main.jsx
    participant App as App
    participant VM as useDashboardViewModel
    participant Data as useDashboardData
    participant LS as useLocalStorageState
    participant API as /api/dashboard

    User->>Main: Open dashboard in browser
    Main->>App: ReactDOM.createRoot(...).render(<App />)
    App->>VM: useDashboardViewModel()
    VM->>Data: useDashboardData()
    VM->>LS: useLocalStorageState(activePage)
    VM->>LS: useLocalStorageState(metric)
    VM->>LS: useLocalStorageState(selectedGeoId)
    Data->>Data: useEffect(() => loadData())
    Data->>API: fetch("/api/dashboard")
    API-->>Data: JSON payload
    Data-->>VM: payload, loading, error, reload
    VM->>VM: derive latestByCity, selectedCity, cityRows
    VM-->>App: view model state
    App-->>User: render Overview / City Trends / Compare page
```

## 10. Dashboard Backend Request Flow

Source file:

- `services/dashboard/server.py`

```mermaid
sequenceDiagram
    autonumber
    actor Browser
    participant Handler as DashboardRequestHandler.do_GET
    participant Build as build_dashboard_payload
    participant Cache as DashboardCache
    participant Load as _load_dashboard_frame
    participant DB as PostgreSQL air_pollution_gold

    Browser->>Handler: GET /api/dashboard
    Handler->>Build: build_dashboard_payload()
    alt cache is fresh
        Build->>Cache: return cached payload
    else cache is stale or empty
        Build->>Load: _load_dashboard_frame()
        Load->>DB: SELECT ... FROM air_pollution_gold ORDER BY geo_id, ts
        DB-->>Load: result set
        Load-->>Build: pandas DataFrame
        Build->>Build: normalize timestamps and sort rows
        Build->>Build: latest_by_city = groupby("geo_id").tail(1)
        Build->>Build: build rows, latestByCity, summary
        Build->>Cache: store payload and refresh timestamp
    end
    Build-->>Handler: payload
    Handler-->>Browser: JSON response
```

## 11. Call Graph Summary

The main happy-path function chain for the ETL pipeline is:

1. `run_pipeline.py`
2. `pipeline.cli.main()`
3. `orchestration.run_pipeline_job()`
4. `run_tracking.create_pipeline_run()`
5. `orchestration.run_extract_stage()`
6. `extract.cities.read_cities()`
7. `extract.geocoding.geocode_city()`
8. `extract.openweather_air_pollution.fetch_air_pollution_history()`
9. `orchestration.run_transform_stage()`
10. `transform.openweather_air_pollution_transform.build_gold_from_raw_records()`
11. `transform.risk_scoring.add_aqi_category()`
12. `transform.risk_scoring.add_risk_score()`
13. `orchestration.run_load_stage()`
14. `load.storage.publish_outputs()`
15. `run_tracking.update_pipeline_run_status()`

## 12. Important Runtime Notes

- PostgreSQL is the system of record for `cities`, `geocoding_cache`, `pipeline_runs`, `raw_air_pollution_responses`, and `air_pollution_gold`.
- The handoff from extract to transform to load is not DB-to-DB. It happens as Python objects and a pandas DataFrame in memory.
- `raw_dir` is still passed around by orchestration, but `fetch_air_pollution_history()` currently ignores it.
- Local Parquet and Azure Blob publishing are optional secondary outputs; PostgreSQL remains the primary gold-data target.
- Prefect is the active orchestration direction; `scheduler.py` remains as a temporary compatibility shim during the transition.
- Configurable recurring scheduling via Prefect deployments is a follow-up capability.
- The dashboard backend reads only from `air_pollution_gold`; it does not call pipeline code directly.
