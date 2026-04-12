# Azure Blob Storage Configuration

This guide explains how to configure the pipeline to publish the gold Parquet
artifact to either:

- local Azurite for development, or
- real Azure Blob Storage for production-style environments

The pipeline already reads Azure Blob settings from environment variables, so
switching targets should not require code changes.

## Environment Variables

The Azure-compatible publish path is controlled by these settings:

```dotenv
WRITE_GOLD_AZURE_BLOB=1
AZURE_STORAGE_CONNECTION_STRING=...
AZURE_BLOB_CONTAINER=gold
AZURE_BLOB_PATH=exports/{table_name}.parquet
```

What each setting does:

- `WRITE_GOLD_AZURE_BLOB=1`
  enables Blob publishing
- `AZURE_STORAGE_CONNECTION_STRING`
  chooses the storage account or emulator target
- `AZURE_BLOB_CONTAINER`
  chooses the destination container
- `AZURE_BLOB_PATH`
  controls the blob naming pattern

The current load layer formats `AZURE_BLOB_PATH` with `{table_name}`, so the
default path becomes:

```text
exports/air_pollution_gold.parquet
```

## Local Azurite Example

Use this when running the local Docker Compose stack with Azurite:

```dotenv
WRITE_GOLD_AZURE_BLOB=1
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://azurite:10000/devstoreaccount1;
AZURE_BLOB_CONTAINER=gold
AZURE_BLOB_PATH=exports/{table_name}.parquet
```

Notes:

- inside Docker Compose, the Blob endpoint uses the service name `azurite`
- host-based tools outside Docker should use `localhost` instead of `azurite`
- the browser explorer in this repo is intended for this local Azurite flow

## Production Azure Blob Example

Use this pattern when targeting a real Azure Storage account:

```dotenv
WRITE_GOLD_AZURE_BLOB=1
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=YOUR_ACCOUNT;AccountKey=YOUR_KEY;EndpointSuffix=core.windows.net
AZURE_BLOB_CONTAINER=gold
AZURE_BLOB_PATH=exports/{table_name}.parquet
```

Notes:

- no code changes are required when switching from Azurite to real Azure
- the main change is the connection string
- you may keep the same container and blob path pattern if they already match
  your deployment needs
- if your production naming convention differs, change only
  `AZURE_BLOB_PATH`

## What Stays the Same Across Local and Production

These behaviors are unchanged regardless of target:

- the pipeline publishes the same gold Parquet artifact
- the target blob container is created if it does not already exist
- the blob path naming stays configurable through `AZURE_BLOB_PATH`
- PostgreSQL can remain the primary gold target while Blob publishing runs as an
  optional secondary export

## Verification

For either environment, verify:

- `WRITE_GOLD_AZURE_BLOB=1` is enabled
- the connection string points to the intended target
- the expected blob appears in the configured container
- the blob path matches the configured `AZURE_BLOB_PATH` pattern

Expected default blob location:

- container: `gold`
- path: `exports/air_pollution_gold.parquet`
