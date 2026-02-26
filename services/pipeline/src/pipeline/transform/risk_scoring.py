from __future__ import annotations
import pandas as pd


def add_aqi_category(df: pd.DataFrame) -> pd.DataFrame:
    # OpenWeather AQI is 1..5 (1=Good, 5=Very Poor)
    mapping = {1: "Good", 2: "Fair", 3: "Moderate", 4: "Poor", 5: "Very Poor"}
    out = df.copy()
    out["aqi_category"] = out["aqi"].map(mapping).fillna("Unknown")
    return out


def add_risk_score(df: pd.DataFrame) -> pd.DataFrame:
    # POC score: combine AQI (1-5) and PM measures
    out = df.copy()
    aqi = out["aqi"].fillna(0).astype(float)
    pm25 = out["pm2_5"].fillna(0).astype(float)
    pm10 = out["pm10"].fillna(0).astype(float)
    o3 = out["o3"].fillna(0).astype(float)
    no2 = out["no2"].fillna(0).astype(float)

    # Simple weighted sum; document and tune later
    score = (aqi * 10.0) + (pm25 * 0.8) + (pm10 * 0.3) + (o3 * 0.05) + (no2 * 0.05)
    out["risk_score"] = score.round(3)
    return out
