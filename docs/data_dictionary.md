# Data Dictionary (POC)

## air_pollution_gold.parquet

| Column | Type | Description |
|---|---:|---|
| ts | timestamp | Observation timestamp (UTC) |
| city | string | City name (from configs) |
| country_code | string | ISO country code (from configs) |
| lat | float | Latitude |
| lon | float | Longitude |
| geo_id | string | Deterministic key: `{city},{country_code}:{lat},{lon}` |
| aqi | int | OpenWeather AQI index (1–5) |
| co | float | Carbon monoxide (μg/m3) |
| no | float | Nitrogen monoxide (μg/m3) |
| no2 | float | Nitrogen dioxide (μg/m3) |
| o3 | float | Ozone (μg/m3) |
| so2 | float | Sulphur dioxide (μg/m3) |
| nh3 | float | Ammonia (μg/m3) |
| pm2_5 | float | PM2.5 (μg/m3) |
| pm10 | float | PM10 (μg/m3) |
| aqi_category | string | Derived category label |
| risk_score | float | Derived score (rule-based in POC) |

> Replace/extend units and definitions based on the exact OpenWeather response fields you use.
