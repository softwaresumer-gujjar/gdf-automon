import uuid
from datetime import datetime
from sqlalchemy import String, Float, DateTime, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class SensorReading(Base):
    """
    TimescaleDB hypertable partitioned by `time`.
    Created via Alembic migration — Alembic creates the table,
    then runs SELECT create_hypertable('sensor_readings', 'time').
    """
    __tablename__ = "sensor_readings"
    __table_args__ = (
        Index("idx_sensor_readings_sensor_time", "sensor_id", "time"),
    )

    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True, nullable=False)
    sensor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sensors.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    channel: Mapped[str] = mapped_column(String(100), primary_key=True, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
