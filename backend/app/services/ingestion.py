"""Write sensor readings to TimescaleDB and evaluate alert rules."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.telemetry import SensorReading
from app.models.alert import AlertRule


async def insert_reading(
    session: AsyncSession,
    sensor_id: str,
    channel: str,
    value: float,
    unit: str,
    ts: str | None = None,
) -> None:
    if ts is None:
        ts = datetime.now(timezone.utc).isoformat()

    try:
        time = datetime.fromisoformat(ts)
    except ValueError:
        time = datetime.now(timezone.utc)

    reading = SensorReading(
        time=time,
        sensor_id=uuid.UUID(sensor_id) if isinstance(sensor_id, str) else sensor_id,
        channel=channel,
        value=value,
        unit=unit,
    )
    session.add(reading)
    await session.commit()

    # Trigger alert evaluation asynchronously (non-blocking)
    from app.services.alert_engine import evaluate_rules
    import asyncio
    asyncio.create_task(evaluate_rules(sensor_id, channel, value, session))
