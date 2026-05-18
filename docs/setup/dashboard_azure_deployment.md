# Dashboard Azure Deployment

This guide explains how the React dashboard is deployed from GitHub to Azure
App Service.

The dashboard deployment has two parts:

- a GitHub Actions workflow in `.github/workflows/dashboard-azure-deploy.yml`
- Azure App Service configuration and GitHub repository secrets

## Why the workflow lives in `.github/workflows`

GitHub Actions only discovers workflow files from the repository's
`.github/workflows/` directory.

The dashboard deployment workflow is:

```text
.github/workflows/dashboard-azure-deploy.yml
```

## What the workflow does

When the workflow runs, it:

1. checks out the repository
2. builds the dashboard container using `services/dashboard/Dockerfile`
3. publishes the image to GitHub Container Registry
4. deploys that image to Azure App Service

The published image is named:

```text
ghcr.io/code-the-dream-school/city-air-tracker-dashboard
```

## When the workflow runs

The workflow runs automatically after changes are merged to `main` when those
changes affect:

- `.github/workflows/dashboard-azure-deploy.yml`
- `services/dashboard/**`

It can also be started manually from the GitHub Actions tab with
`workflow_dispatch`.

## Required GitHub secret

Create this repository secret in GitHub:

```text
AZURE_DASHBOARD_PUBLISH_PROFILE
```

To get the value from Azure:

1. Open the Azure Portal.
2. Open the dashboard App Service.
3. Confirm the App Service name is `city-air-tracker-dashboard`.
4. Click `Get publish profile`.
5. Open the downloaded publish profile file.
6. Copy the entire file contents.
7. In GitHub, open the repository.
8. Go to `Settings` -> `Secrets and variables` -> `Actions`.
9. Create a new repository secret named `AZURE_DASHBOARD_PUBLISH_PROFILE`.
10. Paste the publish profile contents as the secret value.

## Required Azure App Service settings

Set the dashboard runtime environment variables in Azure App Service under:

`Settings` -> `Environment variables`

Use either `DATABASE_URL` or the individual PostgreSQL settings.

Option A:

```dotenv
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/cityair
DASHBOARD_CACHE_TTL_SECONDS=60
PORT=8501
```

Option B:

```dotenv
POSTGRES_HOST=YOUR_SERVER.postgres.database.azure.com
POSTGRES_PORT=5432
POSTGRES_DB=cityair
POSTGRES_USER=YOUR_USER@YOUR_SERVER
POSTGRES_PASSWORD=YOUR_PASSWORD
DASHBOARD_CACHE_TTL_SECONDS=60
PORT=8501
```

For Azure Database for PostgreSQL, the username commonly includes the server
name, such as `appuser@myserver`.

## App Service name

The workflow currently targets this Azure App Service:

```text
city-air-tracker-dashboard
```

If the Azure App Service is renamed, update `AZURE_WEBAPP_NAME` in
`.github/workflows/dashboard-azure-deploy.yml`.

## Verification

After the workflow runs:

1. Open the GitHub Actions run and confirm the build and deploy steps passed.
2. Open the Azure App Service overview page.
3. Restart the app if Azure prompts for it.
4. Open the App Service URL.
5. Confirm the dashboard loads.
6. Confirm `/api/health` returns a healthy response.
7. Confirm `/api/dashboard` returns data or an empty dashboard payload.

If the site loads but the dashboard API fails, check the App Service logs and
confirm the PostgreSQL environment variables point to the Azure PostgreSQL
server.
