# Architecture (OpenWeather 72h History)

## Component diagram (PlantUML)

```plantuml
@startuml
skinparam componentStyle rectangle

package "City Air Tracker (Monorepo)" {
  [Pipeline CLI\n(run_pipeline.py)] as cli
  component "Geocoding\n(OW Geocoding API)\ngeocoding.py" as geo
  component "Air Pollution Extractor\n(history 72h)\nopenweather_air_pollution.py" as ex
  component "Transform\nopenweather_air_pollution_transform.py" as tr
  component "Load\nstorage.py" as ld
  database "Raw Cache\n(data/raw/openweather/...)" as raw
  database "Gold Dataset\n(data/gold/air_pollution_gold.parquet)" as gold
  database "Postgres (optional)" as pg
  component "Dashboard\n(Streamlit)" as dash
  file "cities.csv" as cities
}

cities --> cli
cli --> geo
geo --> raw : cache coords
cli --> ex
ex --> raw : write raw JSON + manifest
cli --> tr
tr --> gold : write parquet
ld --> pg : optional
dash --> gold : read

@enduml
```

## Sequence diagram (PlantUML)

```plantuml
@startuml
actor User
participant "run_pipeline.py" as CLI
participant "geocoding.py" as GEO
participant "openweather_air_pollution.py" as EX
participant "transform" as TR
participant "load" as LD
database "data/raw" as RAW
database "data/gold" as GOLD
database "Postgres" as PG
file "configs/cities.csv" as CITIES

User -> CLI: run --history-hours 72
CLI -> CITIES: read list
loop per city
  CLI -> GEO: city+country -> lat/lon
  GEO -> RAW: cache geocode result
  CLI -> EX: fetch history(lat,lon,start,end)
  EX -> RAW: write response json + manifest
end
CLI -> TR: parse raw json -> tidy DF
TR -> GOLD: write parquet
CLI -> LD: optionally publish to DB
LD -> PG: write table (if enabled)
@enduml
```
