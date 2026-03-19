# Docker Compose Azure Local Development

This project's Docker Compose setup includes an `azurite` container so contributors can run an Azure-compatible blob emulator on their own machine.

## What This Ticket Adds

- An `azurite` service in `docker-compose.yml`
- Compose-level Azure emulator environment variables for the `pipeline` and `dashboard` services
- Default local development values in `.env.example`

## Current Behavior

The pipeline still defaults to `STORAGE_BACKEND=local`, so the gold parquet dataset is written to:

`/app/data/gold/air_pollution_gold.parquet`

That keeps the current developer workflow stable while giving the project a ready-to-use Azure-compatible local environment.

## Local Endpoints

When Docker Compose is running, Azurite exposes:

- Blob service: `http://localhost:10000/devstoreaccount1`
- Queue service: `http://localhost:10001/devstoreaccount1`
- Table service: `http://localhost:10002/devstoreaccount1`

Inside Compose service-to-service networking, containers should use:

`http://azurite:10000/devstoreaccount1`

## Environment Variables

The Docker Compose setup passes these Azure-compatible settings into the application containers:

- `AZURE_STORAGE_ACCOUNT_NAME=devstoreaccount1`
- `AZURE_STORAGE_ACCOUNT_KEY=Eby8vdM02xNOcqFeqCnf2FlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==`
- `AZURE_STORAGE_BLOB_ENDPOINT=http://azurite:10000/devstoreaccount1`
- `AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFeqCnf2FlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://azurite:10000/devstoreaccount1;`
- `AZURE_STORAGE_CONTAINER=cityair`
- `AZURE_STORAGE_PREFIX=gold`

These defaults are for local development only.

## How To Run

1. Copy `.env.example` to `.env`.
2. Set `OPENWEATHER_API_KEY`.
3. Start the stack with `docker compose up --build`.
4. Open the dashboard at `http://localhost:8501`.

## Smoke Test

An opt-in Docker smoke test is available at:

`services/pipeline/tests/test_docker_azurite_smoke.py`

Run it from the repository root with:

```bash
RUN_DOCKER_SMOKE_TESTS=1 pytest services/pipeline/tests/test_docker_azurite_smoke.py -q
```

The test:

- pulls `mcr.microsoft.com/azure-storage/azurite` if it is not already present locally
- starts the `azurite` Compose service if needed
- waits for `localhost:10000` to accept TCP connections
- verifies the Azurite container is running
- cleans up the container only if the test started it

## Notes For Contributors

- Keep `STORAGE_BACKEND=local` unless you are actively working on Azure-backed storage behavior.
- Prefer the `azurite` hostname inside containers instead of `localhost`.
- Do not use the emulator connection string for real Azure environments.
