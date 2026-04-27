"""convert sensor_readings to TimescaleDB hypertable (skipped if TimescaleDB not installed)

Revision ID: 002
Revises: 001
Create Date: 2026-04-28
"""
from alembic import op
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def _timescale_available(conn) -> bool:
    try:
        result = conn.execute(text(
            "SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'"
        ))
        return result.fetchone() is not None
    except Exception:
        return False


def upgrade() -> None:
    conn = op.get_bind()
    if not _timescale_available(conn):
        print("[002] TimescaleDB not installed — skipping hypertable setup.")
        return

    conn.execute(text("""
        SELECT create_hypertable(
            'sensor_readings', 'time',
            chunk_time_interval => INTERVAL '7 days',
            if_not_exists => TRUE
        )
    """))

    conn.execute(text("""
        ALTER TABLE sensor_readings SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'sensor_id, channel'
        )
    """))

    conn.execute(text("""
        SELECT add_compression_policy(
            'sensor_readings',
            INTERVAL '90 days',
            if_not_exists => TRUE
        )
    """))

    conn.execute(text("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS sensor_readings_5min
        WITH (timescaledb.continuous) AS
        SELECT
            time_bucket('5 minutes', time) AS bucket,
            sensor_id,
            channel,
            AVG(value) AS avg_value,
            MIN(value) AS min_value,
            MAX(value) AS max_value,
            COUNT(*) AS reading_count
        FROM sensor_readings
        GROUP BY bucket, sensor_id, channel
        WITH NO DATA
    """))

    conn.execute(text("""
        SELECT add_continuous_aggregate_policy(
            'sensor_readings_5min',
            start_offset => INTERVAL '1 hour',
            end_offset => INTERVAL '5 minutes',
            schedule_interval => INTERVAL '5 minutes',
            if_not_exists => TRUE
        )
    """))

    print("[002] TimescaleDB hypertable configured.")


def downgrade() -> None:
    conn = op.get_bind()
    if not _timescale_available(conn):
        return
    conn.execute(text("DROP MATERIALIZED VIEW IF EXISTS sensor_readings_5min"))
