import os
from pathlib import Path
import pandas as pd
import streamlit as st

st.set_page_config(page_title="City Air Tracker", layout="wide")
st.title("City Air Tracker — OpenWeather 72h History")
st.caption("POC dashboard reading the gold dataset produced by the pipeline.")

data_path = Path(os.getenv("DASHBOARD_DATA_PATH", "/app/data/gold/air_pollution_gold.parquet"))

if not data_path.exists():
    st.warning(f"Gold dataset not found at {data_path}. Run the pipeline first.")
    st.stop()

df = pd.read_parquet(data_path)
st.metric("Rows", len(df))
st.metric("Cities", df["geo_id"].nunique() if len(df) else 0)

st.dataframe(df.sort_values(["geo_id", "ts"], ascending=[True, False]).head(50), use_container_width=True)

st.info("See pages: City Trends / Compare Cities")
