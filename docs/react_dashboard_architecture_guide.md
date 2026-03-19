# React Dashboard Architecture Guide

This document explains the React dashboard implementation created on the `AIR-007.1` migration branch.

It is included here as a reference for the React version of the dashboard, even though this branch still uses the older Streamlit implementation at runtime.

## Purpose

The React dashboard was introduced to support a friendlier, more modern student-facing UI than the original Streamlit version.

The React implementation keeps the same core data source:

- the pipeline still writes a gold parquet file
- the dashboard still reads that prepared dataset
- a small Python server sits between the parquet file and the React frontend

That design keeps the business logic in the pipeline while letting the UI become more flexible.

## High-Level Architecture

The React dashboard is split into three main parts:

1. frontend build tooling
2. React UI code
3. lightweight Python dashboard server

At a high level, the flow looks like this:

1. Docker builds the React frontend with Vite.
2. The built static files are copied into the dashboard image.
3. A Python HTTP server serves those files.
4. The same Python server reads the parquet dataset.
5. The React app fetches dashboard JSON from `/api/dashboard`.
6. The browser renders charts, cards, rankings, and tables from that payload.

## Main Files And Modules

### `services/dashboard/frontend/package.json`

This file defines the JavaScript dependencies and scripts for the React dashboard.

Important sections:

- `scripts.dev`
  Starts a Vite development server.

- `scripts.build`
  Builds the production frontend assets into a `dist` folder.

- `scripts.preview`
  Serves the built Vite app for previewing.

### `services/dashboard/frontend/vite.config.js`

This file configures Vite, which is the frontend build tool.

In this project it:

- enables the React plugin
- sends build output to `dist`
- clears old build output before writing a new build

### `services/dashboard/frontend/index.html`

This is the HTML shell for the React app.

It does three important things:

- defines the `root` element where React mounts
- loads the dashboard fonts
- includes the JavaScript entry point

### `services/dashboard/frontend/src/main.jsx`

This is the frontend entry point.

Its job is simple:

- import React
- import ReactDOM
- import the root `App` component
- import the global stylesheet
- render the app into the page

### `services/dashboard/frontend/src/App.jsx`

This is the main frontend module.

It contains:

- top-level app state
- page navigation
- city selection logic
- metric selection logic
- data fetching from `/api/dashboard`
- the main dashboard components

This file is intentionally large in the first iteration because it keeps the migration simple.
Later, it could be split into smaller files such as:

- `components/`
- `charts/`
- `hooks/`
- `utils/`

### `services/dashboard/frontend/src/styles.css`

This is the main stylesheet for the React dashboard.

It defines:

- the visual theme
- card styling
- layout grids
- sidebar navigation
- chart and table presentation
- responsive behavior

The styling aims for a cheerful “happy widget UI” feel for students.

### `services/dashboard/server.py`

This is the lightweight backend for the dashboard.

It is not a full API framework like Flask or FastAPI.
Instead, it uses Python’s built-in HTTP server tools.

Its responsibilities are:

- read the gold parquet file
- normalize pandas/numpy values so they are JSON-safe
- build a dashboard payload
- cache the payload until the parquet file changes
- serve `/api/health`
- serve `/api/dashboard`
- serve the built React files from `static/`
- return `index.html` for frontend routes

### `services/dashboard/requirements.txt`

This file contains the Python dependencies needed by the React dashboard server.

In the migration branch it is intentionally small because the server only needs:

- `pandas`
- `pyarrow`

### `services/dashboard/Dockerfile`

This Dockerfile is a multi-stage build:

1. a Node stage builds the React frontend
2. a Python stage serves the built frontend and dashboard API

This keeps the final runtime image smaller than shipping the full Node toolchain in the final container.

## Frontend Architecture

The React app is organized around one main screen shell plus three page modes:

- Overview
- City Trends
- Compare Cities

The app behaves more like a single-page application than a traditional multi-page website.

Instead of changing browser routes, it changes the visible dashboard section through local component state.

### Top-level state in `App.jsx`

The main `App` component tracks:

- `payload`
  The full JSON response from `/api/dashboard`

- `loading`
  Whether the dashboard is waiting for API data

- `error`
  Whether the dashboard failed to load

- `activePage`
  Which dashboard view is visible

- `metric`
  Which metric is selected for charts and comparisons

- `selectedGeoId`
  Which city is selected

### Derived data

The app uses memoized derived values to avoid recomputing everything on every render.

Examples:

- the selected city record
- all rows for the selected city
- sorted city comparison lists

This keeps the UI responsive while still being easy to understand.

## Main UI Components

The React version uses a component-oriented structure inside `App.jsx`.

The main conceptual components are:

### `WidgetCard`

Used for colorful summary cards such as:

- cities monitored
- average AQI
- last refresh
- highest risk city

This component is mainly a reusable visual card container.

### `StatPill`

A compact label/value widget used inside larger cards.

Examples:

- PM2.5
- PM10
- risk score
- 24h average

### `CityRankCard`

Shows where the selected city ranks compared with the others.

This helps students move from “what is my city doing?” to “how does it compare?”

### `LatestSnapshot`

The main “current city status” panel.

It combines:

- city identity
- AQI badge
- large AQI number
- key supporting metrics
- last updated time
- ranking information

### `TrendPanel`

Renders the 72-hour chart for the selected metric.

### `ObservationsTable`

Shows recent rows in a table so the user can inspect the actual data behind the chart.

### `OverviewPage`

Builds the summary dashboard view.

### `CityTrendsPage`

Builds the city-specific analysis view.

### `ComparePage`

Builds the cross-city comparison view.

## Backend Architecture

The Python server is intentionally minimal.

It has two goals:

1. provide data to the React app
2. serve the frontend build output

### Why a lightweight Python server?

This project already uses Python for the pipeline, and the dashboard data comes from a parquet file.

So the simplest architecture is:

- Python reads parquet well
- React handles the UI well
- a tiny Python server glues them together

That avoids introducing a larger backend framework too early.

### Key backend functions

#### `build_dashboard_payload()`

This is the core backend function.

It:

- loads the parquet file
- sorts and groups the data
- builds per-city latest rows
- computes summary values
- returns a JSON-ready dictionary

#### `_normalize_value()`

This function converts pandas and numpy values into JSON-safe Python values.

That matters because raw pandas/numpy values often cannot be serialized directly with `json.dumps()`.

#### `DashboardRequestHandler`

This is the HTTP request handler.

It:

- responds to `/api/health`
- responds to `/api/dashboard`
- serves static frontend files
- falls back to `index.html` for frontend requests

## Libraries Used In The UI

The React implementation uses a small set of libraries on purpose.

### `react`

What it is:
- the core UI library

What it does here:
- defines components
- manages state
- updates the UI when the data changes

Why it matters:
- gives much more layout and styling flexibility than Streamlit

### `react-dom`

What it is:
- the library that connects React to the browser DOM

What it does here:
- mounts the React app into the `root` element in `index.html`

### `vite`

What it is:
- a frontend build tool and development server

What it does here:
- builds the frontend assets
- processes the React app for production
- outputs the final static files used by the Python server

Why it was chosen:
- fast startup
- simple config
- great fit for small-to-medium React apps

### `@vitejs/plugin-react`

What it is:
- the Vite plugin that enables React support

What it does here:
- handles JSX transformation
- supports React development/build behavior properly

### `lucide-react`

What it is:
- a React icon library

What it does here:
- provides the dashboard icons used in cards and navigation

Examples in the React dashboard:

- `Home`
- `TrendingUp`
- `BarChart3`
- `AlertTriangle`
- `Wind`
- `Sparkles`

Why it was chosen:
- lightweight
- modern visual style
- easy to use as React components

### `recharts`

What it is:
- a React charting library

What it does here:
- renders the line and bar charts in the dashboard

Examples in the React dashboard:

- 72-hour trend line chart
- city comparison bar chart
- overview ranking chart

Why it was chosen:
- easy to compose with React
- beginner-friendly compared with more complex charting libraries
- good enough for the dashboard’s current analytical needs

### Browser APIs and built-in JavaScript features

The app also relies on standard browser/runtime features such as:

- `fetch`
  to call `/api/dashboard`

- `localStorage`
  to remember the last selected city

- `Intl.DateTimeFormat`
  to format timestamps for display

These are not extra libraries, but they are important parts of how the UI works.

## Why This Architecture Works Well

This React dashboard architecture works well for the project because:

- the pipeline remains the source of data preparation logic
- the dashboard stays mostly presentation-focused
- the backend remains small and understandable
- the frontend becomes much more flexible visually
- students can learn from a clearer separation between data processing and UI rendering

## Tradeoffs

The React architecture also introduces some complexity compared with Streamlit:

- there is now a frontend build step
- there are more files and moving parts
- Docker needs to build both frontend and Python runtime layers
- contributors need some React familiarity for dashboard UI work

So the tradeoff is:

- more power and better UI control
- in exchange for more implementation complexity

## Practical Summary

The React dashboard is best understood as:

- React for presentation
- Python for parquet reading and lightweight API responses
- Docker for packaging the full dashboard service

That combination gives the project a more professional and extensible dashboard without turning it into a full multi-service backend/frontend platform.
