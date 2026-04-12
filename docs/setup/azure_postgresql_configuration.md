# Azure Database for PostgreSQL Configuration

This guide explains how to point the pipeline at managed Azure Database for
PostgreSQL while keeping the existing DB-first runtime behavior unchanged.

The same PostgreSQL code path is used for:

- local Docker or host-based PostgreSQL development
- managed Azure Database for PostgreSQL environments

Switching targets should only require environment variable changes.

## Environment Variables

The PostgreSQL runtime path uses these settings:

```dotenv
USE_POSTGRES=1
POSTGRES_HOST=...
POSTGRES_PORT=5432
POSTGRES_DB=cityair
POSTGRES_USER=...
POSTGRES_PASSWORD=...
POSTGRES_SSLMODE=
POSTGRES_SSLROOTCERT=
```

What each setting does:

- `USE_POSTGRES=1`
  keeps PostgreSQL as the primary gold target
- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`
  choose the database server and database name
- `POSTGRES_USER`, `POSTGRES_PASSWORD`
  provide database credentials
- `POSTGRES_SSLMODE`
  adds an SSL mode to the SQLAlchemy connection URL when needed
- `POSTGRES_SSLROOTCERT`
  optionally points to a root certificate file for stricter SSL validation

## Local Development Example

Use these values for local host-based PostgreSQL development:

```dotenv
USE_POSTGRES=1
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=cityair
POSTGRES_USER=cityair
POSTGRES_PASSWORD=cityair
POSTGRES_SSLMODE=
POSTGRES_SSLROOTCERT=
```

Notes:

- leaving `POSTGRES_SSLMODE` empty preserves the current local behavior
- Docker Compose service-based development can continue using `POSTGRES_HOST=postgres`

## Azure Database for PostgreSQL Example

Use a configuration like this for managed Azure Database for PostgreSQL:

```dotenv
USE_POSTGRES=1
POSTGRES_HOST=YOUR_SERVER.postgres.database.azure.com
POSTGRES_PORT=5432
POSTGRES_DB=cityair
POSTGRES_USER=YOUR_USER@YOUR_SERVER
POSTGRES_PASSWORD=YOUR_PASSWORD
POSTGRES_SSLMODE=require
POSTGRES_SSLROOTCERT=
```

Notes:

- `POSTGRES_SSLMODE=require` is the important cloud-specific change for the
  common Azure case
- Azure usernames often include the server name, such as
  `appuser@myserver`
- if your environment requires a root certificate file, set
  `POSTGRES_SSLROOTCERT` to its path

## What Stays the Same

When switching from local PostgreSQL to Azure Database for PostgreSQL:

- the DB-first behavior does not change
- PostgreSQL remains the primary gold target
- the pipeline still uses the same runtime orchestration path
- local Docker/Postgres settings remain valid for development

## Verification

To verify the Azure PostgreSQL configuration:

- confirm the environment values point to the intended Azure server
- confirm `POSTGRES_SSLMODE=require` or the required SSL mode for your setup
- run the usual pipeline command
- verify rows appear in the expected PostgreSQL tables, such as:
  - `pipeline_runs`
  - `raw_air_pollution_responses`
  - `air_pollution_gold`
