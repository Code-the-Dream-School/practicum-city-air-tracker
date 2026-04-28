'''Tests for pipeline.ml.features — verifies feature shape, per-city scoping,
    short-history NaN behavior, determinism, and input-mutation safety.'''
from datetime import datetime, timezone
import pandas as pd
import pytest
from pipeline.ml.features import add_ml_features, add_time_features, add_lag_features, add_rolling_features


def _make_df(rows: list[tuple[int, int, float]]) -> pd.DataFrame:
    return pd.DataFrame([
        {'city_id': c, 'ts': datetime(2026, 4, 28, h, tzinfo=timezone.utc), 'pm2_5': p}
        for (c, h, p) in rows
    ])


def test_add_ml_features_adds_all_five_columns():
    '''add_ml_features adds all 5 expected feature columns.'''
    df = _make_df([
        (1, 0, 10.0),
        (1, 1, 20.0),
        (2, 0, 30.0),
    ])
    result = add_ml_features(df)
    expected_cols = {'hour_of_day', 'day_of_week', 'pm2_5_prev_1h', 'pm2_5_roll_3h', 'pm2_5_roll_12h'}
    assert expected_cols.issubset(result.columns)


def test_lag_first_row_per_city_is_nan():
    '''The first row for each city has NaN in the lag feature, since no prior
    observation exists for that city.'''
    df = _make_df([
        (1, 0, 10.0),
        (1, 1, 20.0),
        (2, 0, 30.0),
        (2, 1, 40.0),
    ])
    result = add_lag_features(df)
    for city_id in [1, 2]:
        city_rows = result[result['city_id'] == city_id].sort_values('ts')
        first_row = city_rows.iloc[0]
        assert pd.isna(first_row['pm2_5_prev_1h'])
        assert city_rows.iloc[1]['pm2_5_prev_1h'] == city_rows.iloc[0]['pm2_5']


def test_lag_handles_single_row_city():
    '''A city with only one row of history produces NaN for pm2_5_prev_1h
    without crashing'''
    df = _make_df([
        (1, 0, 10.0),   # the only row of history for city 1
    ])
    result = add_lag_features(df)
    assert pd.isna(result.iloc[0]['pm2_5_prev_1h'])


def test_rolling_handles_single_row_city():
    '''A city with only one row gets its own value as the rolling mean
    (min_periods=1 semantics — no NaN from short history).'''
    df = _make_df([
        (1, 0, 42.0),
    ])
    result = add_rolling_features(df)
    assert result.iloc[0]['pm2_5_roll_3h'] == 42.0
    assert result.iloc[0]['pm2_5_roll_12h'] == 42.0


def test_features_do_not_leak_between_cities():
    '''Lag and rolling features are computed per city_id, so one city's history
    never leaks into another city's features.'''
    df = _make_df([
        (1, 0, 10.0),
        (1, 1, 20.0),
        (2, 0, 1000.0),
        (2, 1, 2000.0),
    ])
    result = add_ml_features(df)

    # City 1's lag feature is based on its own history, not city 2's
    assert result[result['city_id'] == 1].iloc[1]['pm2_5_prev_1h'] == 10.0

    # City 2's lag feature is based on its own history, not city 1's
    assert result[result['city_id'] == 2].iloc[1]['pm2_5_prev_1h'] == 1000.0

    # City 1's rolling features are based on its own history, not city 2's
    city_1_roll_3h = result[result['city_id'] == 1]['pm2_5_roll_3h'].tolist()
    assert city_1_roll_3h == [10.0, (10.0 + 20.0) / 2]

    # City 2's rolling features are based on its own history, not city 1's
    city_2_roll_3h = result[result['city_id'] == 2]['pm2_5_roll_3h'].tolist()
    assert city_2_roll_3h == [1000.0, (1000.0 + 2000.0) / 2]


def test_features_are_deterministic_under_shuffle():
    '''Output features are identical regardless of input row order, since
    features are computed per city_id with a deterministic sort by ts.'''
    df_ordered = _make_df([
        (1, 0, 10.0),
        (1, 1, 20.0),
        (1, 2, 30.0),
        (2, 0, 1000.0),
        (2, 1, 2000.0),
        (2, 2, 3000.0),
    ])
    df_shuffled = df_ordered.sample(frac=1, random_state=42).reset_index(drop=True)

    result_ordered = add_ml_features(df_ordered).sort_values(['city_id', 'ts']).reset_index(drop=True)
    result_shuffled = add_ml_features(df_shuffled).sort_values(['city_id', 'ts']).reset_index(drop=True)

    pd.testing.assert_frame_equal(result_ordered, result_shuffled)


def test_raises_on_missing_required_column():
    '''add_ml_features raises a KeyError if the input DataFrame is missing any
    required column.'''
    df = pd.DataFrame({
        'city_id': [1],
        'ts': [pd.Timestamp("2026-04-05T00:00:00Z")],
        # 'pm2_5' column is missing
    })
    with pytest.raises(KeyError, match="missing required column"):
        add_ml_features(df)


def test_input_dataframe_is_not_mutated():
    '''The input DataFrame is not mutated by add_ml_features, add_lag_features,
    or add_rolling_features — a new DataFrame with added columns is returned.'''
    df = _make_df([
        (1, 0, 10.0),
        (1, 1, 20.0),
    ])
    df_before = df.copy()
    _ = add_ml_features(df)
    _ = add_lag_features(df)
    _ = add_rolling_features(df)
    pd.testing.assert_frame_equal(df, df_before)