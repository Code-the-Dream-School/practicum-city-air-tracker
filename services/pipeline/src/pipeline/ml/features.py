'''This module contains functions for feature engineering for machine learning models in the pipeline. 
   It takes in 3 columns from OpenWeather data (city_id, ts, pm2_5) and gives output with 5 columns added namely
        1. hour_of_day
        2. day_of_week
        3. pm2_5_prev_1h
        4. pm2_5_roll_3h
        5. pm2_5_roll_12h
    Features are computed per city_id and are deterministic'''
from __future__ import annotations
import pandas as pd


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    '''Add calendar features derived from the ts timestamp.
    
    Adds:
        hour_of_day: int 0-23, hour of day in UTC.
        day_of_week: int 0-6, Monday=0 (pandas convention).

    These features are deterministic and capture the daily rhythm
    (rush-hour traffic, heating cycles) and weekly rhythm (weekday vs
    weekend) in air quality. Both are pulled directly from `ts` and do
    not depend on any other row, so they are safe even on short history.
    '''
    out = df.copy()
    out['hour_of_day'] = out['ts'].dt.hour
    out['day_of_week'] = out['ts'].dt.dayofweek
    return out


def add_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    '''Add the per-city PM2.5 lag feature.

    Adds:
        pm2_5_prev_1h: float. PM2.5 from the previous hour for the same
            city. NaN for the first row of each city (no prior observation
            exists — this is the explicit short-history behavior).

    Notes:
        - The lag is computed per city_id so one city's history never
        leaks into another city's row.
        - Input rows are sorted by (city_id, ts) defensively before
        shifting, so the output is identical regardless of the input
        row order. Determinism is required by parent story #103.
    '''
    out = df.copy()
    sorted_df = out.sort_values(['city_id', 'ts'])
    out['pm2_5_prev_1h'] = sorted_df.groupby('city_id')['pm2_5'].shift(1)
    return out


def add_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    '''Add the per-city PM2.5 rolling mean features.

    Adds:
        pm2_5_roll_3h: float. Trailing 3-hour mean of PM2.5 for the same
            city, inclusive of the current hour. With min_periods=1, the
            mean is computed over whatever observations are available so
            far: 1 value at row 1, 2 values at row 2, the full 3-hour
            window from row 3 onward. No NaN is produced from short history.
        pm2_5_roll_12h: float. Trailing 12-hour mean of PM2.5 for the same
            city, inclusive of the current hour. Same partial-window
            semantics as pm2_5_roll_3h — rows 1 through 11 of each city
            use whatever data is available so far.

    Notes:
        - Rolling means are computed per city_id, so one city's history
        never leaks into another city's row.
        - Input rows are sorted by (city_id, ts) defensively before the
        rolling computation, so the output is identical regardless of
        input row order. Determinism is required by parent story #103.
        - pandas' rolling.mean() skips NaN values within a window, so a
        single missing PM2.5 reading does not poison the window mean.
    '''
    out = df.copy()
    sorted_df = out.sort_values(['city_id', 'ts'])
    out['pm2_5_roll_3h'] = sorted_df.groupby('city_id')['pm2_5'].rolling(window=3, min_periods=1).mean().reset_index(level=0, drop=True)
    out['pm2_5_roll_12h'] = sorted_df.groupby('city_id')['pm2_5'].rolling(window=12, min_periods=1).mean().reset_index(level=0, drop=True)
    return out


def add_ml_features(df: pd.DataFrame) -> pd.DataFrame:
    '''Add all 5 deterministic ML features to a city-air-quality DataFrame.

    This is the public entry point for the ml/features module. It composes
    the three smaller helpers in order: add_time_features → add_lag_features
    → add_rolling_features. The input DataFrame is never mutated — each
    helper returns a new copy.

    Required input columns:
        city_id (int), ts (UTC datetime), pm2_5 (float; may contain NaN).

    Adds: hour_of_day, day_of_week, pm2_5_prev_1h, pm2_5_roll_3h, pm2_5_roll_12h.

    Raises:
        KeyError — if any required input column is missing. Failing fast
        here is friendlier than producing a confusing pandas error deeper
        in the chain.
    '''
    required = {'city_id', 'ts', 'pm2_5'}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"add_ml_features is missing required columns: {sorted(missing)}")
    out = add_time_features(df)
    out = add_lag_features(out)
    out = add_rolling_features(out)
    return out