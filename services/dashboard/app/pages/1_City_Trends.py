import os
from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

st.title("City Trends (72h)")
data_path = Path(os.getenv("DASHBOARD_DATA_PATH", "/app/data/gold/air_pollution_gold.parquet"))
df = pd.read_parquet(data_path)

geo = st.selectbox("City", sorted(df["geo_id"].unique()))
sub = df[df["geo_id"] == geo].sort_values("ts")

metric = st.selectbox("Metric", ["aqi", "pm2_5", "pm10", "risk_score"])
fig = px.line(sub, x="ts", y=metric, title=f"{metric} over time")
st.plotly_chart(fig, use_container_width=True)

st.dataframe(sub[["ts","aqi","aqi_category","pm2_5","pm10","risk_score"]].tail(48), use_container_width=True)
