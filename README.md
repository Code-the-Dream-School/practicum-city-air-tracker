# City Air Tracker — OpenWeather (72h History) Data Pipeline

This repo is a **Code the Dream**-friendly scaffold for a **batch ETL data pipeline** that:
1) **Geocodes** global cities → lat/lon
2) Pulls **OpenWeather Air Pollution (Historical)** data for the last **72 hours**
3) **Transforms** raw JSON into a tidy **gold** dataset
4) **Loads** to Parquet (and optionally Postgres)
5) Serves a simple **Streamlit dashboard** that reads the gold dataset

## Quickstart (Docker Compose — recommended)

1. Create env file
```bash
cp .env.example .env
# Set OPENWEATHER_API_KEY in .env
```

2. Run everything
```bash
docker compose up --build
```

- Dashboard: http://localhost:8501
- Gold output: `./data/gold/air_pollution_gold.parquet`
- Raw cache: `./data/raw/openweather/...`

## Quickstart (Local Python)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Set OPENWEATHER_API_KEY and local paths (see .env.example)

python services/pipeline/run_pipeline.py --source openweather --history-hours 72
streamlit run services/dashboard/app/Home.py
```

## Configure cities

Edit `configs/cities.csv`:

```csv
city,country_code,state
Toronto,CA,
Paris,FR,
Lagos,NG,
Sydney,AU,NSW
```

> For global cities, **country_code is required** to disambiguate.

## Docs / diagrams
- `docs/architecture.md` — component + sequence diagrams (PlantUML)
- `docs/data_flow_diagram.md` — data flow diagram (PlantUML)

