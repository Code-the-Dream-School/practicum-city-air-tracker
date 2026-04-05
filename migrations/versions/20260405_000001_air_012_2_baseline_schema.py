"""AIR-012.2 baseline PostgreSQL schema."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260405_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cities",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("city", sa.Text(), nullable=False),
        sa.Column("country_code", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "uq_cities_city_country_state",
        "cities",
        ["city", "country_code", "state"],
        unique=True,
        postgresql_nulls_not_distinct=True,
    )

    op.create_table(
        "geocoding_cache",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("city_id", sa.BigInteger(), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("lat", sa.Numeric(9, 6), nullable=False),
        sa.Column("lon", sa.Numeric(9, 6), nullable=False),
        sa.Column("provider_name", sa.Text(), nullable=True),
        sa.Column("provider_state", sa.Text(), nullable=True),
        sa.Column("provider_country", sa.Text(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("city_id", name="uq_geocoding_cache_city_id"),
    )

    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("history_hours", sa.Integer(), nullable=False),
        sa.Column("window_start_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("city_count", sa.Integer(), nullable=True),
        sa.Column("raw_response_count", sa.Integer(), nullable=True),
        sa.Column("gold_row_count", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("run_id", name="uq_pipeline_runs_run_id"),
    )

    op.create_table(
        "raw_air_pollution_responses",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("pipeline_run_id", sa.BigInteger(), nullable=False),
        sa.Column("city_id", sa.BigInteger(), nullable=False),
        sa.Column("geo_id", sa.Text(), nullable=False),
        sa.Column("lat", sa.Numeric(9, 6), nullable=False),
        sa.Column("lon", sa.Numeric(9, 6), nullable=False),
        sa.Column("request_url", sa.Text(), nullable=False),
        sa.Column("request_start_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_end_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("record_count", sa.Integer(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["pipeline_run_id"], ["pipeline_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "city_id",
            "request_start_utc",
            "request_end_utc",
            name="uq_raw_air_pollution_city_window",
        ),
    )
    op.create_index(
        "ix_raw_air_pollution_responses_pipeline_run_id",
        "raw_air_pollution_responses",
        ["pipeline_run_id"],
        unique=False,
    )

    op.create_table(
        "air_pollution_gold",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("pipeline_run_id", sa.BigInteger(), nullable=False),
        sa.Column("raw_response_id", sa.BigInteger(), nullable=True),
        sa.Column("city_id", sa.BigInteger(), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("city", sa.Text(), nullable=False),
        sa.Column("country_code", sa.Text(), nullable=False),
        sa.Column("lat", sa.Numeric(9, 6), nullable=False),
        sa.Column("lon", sa.Numeric(9, 6), nullable=False),
        sa.Column("geo_id", sa.Text(), nullable=False),
        sa.Column("aqi", sa.Integer(), nullable=True),
        sa.Column("co", sa.Numeric(12, 4), nullable=True),
        sa.Column("no", sa.Numeric(12, 4), nullable=True),
        sa.Column("no2", sa.Numeric(12, 4), nullable=True),
        sa.Column("o3", sa.Numeric(12, 4), nullable=True),
        sa.Column("so2", sa.Numeric(12, 4), nullable=True),
        sa.Column("nh3", sa.Numeric(12, 4), nullable=True),
        sa.Column("pm2_5", sa.Numeric(12, 4), nullable=True),
        sa.Column("pm10", sa.Numeric(12, 4), nullable=True),
        sa.Column("pm2_5_24h_avg", sa.Numeric(12, 4), nullable=True),
        sa.Column("aqi_category", sa.Text(), nullable=False),
        sa.Column("risk_score", sa.Numeric(12, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["pipeline_run_id"], ["pipeline_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["raw_response_id"], ["raw_air_pollution_responses.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("geo_id", "ts", name="uq_air_pollution_gold_geo_id_ts"),
    )
    op.create_index("ix_air_pollution_gold_city_id", "air_pollution_gold", ["city_id"], unique=False)
    op.create_index("ix_air_pollution_gold_ts", "air_pollution_gold", ["ts"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_air_pollution_gold_ts", table_name="air_pollution_gold")
    op.drop_index("ix_air_pollution_gold_city_id", table_name="air_pollution_gold")
    op.drop_table("air_pollution_gold")

    op.drop_index("ix_raw_air_pollution_responses_pipeline_run_id", table_name="raw_air_pollution_responses")
    op.drop_table("raw_air_pollution_responses")

    op.drop_table("pipeline_runs")
    op.drop_table("geocoding_cache")

    op.drop_index("uq_cities_city_country_state", table_name="cities")
    op.drop_table("cities")
