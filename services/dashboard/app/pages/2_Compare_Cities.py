import os
from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

st.title("Compare Cities")
data_path = Path(os.getenv("DASHBOARD_DATA_PATH", "/app/data/gold/air_pollution_gold.parquet"))
df = pd.read_parquet(data_path)

latest = df.sort_values("ts").groupby("geo_id").tail(1)

metric = st.selectbox("Metric", ["aqi", "pm2_5", "pm10", "risk_score"])
fig = px.bar(latest.sort_values(metric, ascending=False), x="geo_id", y=metric, title="Latest value by city")
st.plotly_chart(fig, use_container_width=True)

st.dataframe(latest[["geo_id","ts","aqi","aqi_category","pm2_5","pm10","risk_score"]].sort_values(metric, ascending=False), use_container_width=True)
