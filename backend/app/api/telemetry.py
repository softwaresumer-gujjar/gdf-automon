"""Telemetry query API — /api/telemetry"""
import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.telemetry import SensorReading

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.get("")
async def get_telemetry(
    sensor_id: uuid.UUID,
    channel: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(default=1000, le=10000),
    db: AsyncSession = Depends(get_db),
):
    if start is None:
        start = datetime.now(timezone.utc) - timedelta(hours=1)
    if end is None:
        end = datetime.now(timezone.utc)

    conditions = [
        SensorReading.sensor_id == sensor_id,
        SensorReading.time >= start,
        SensorReading.time <= end,
    ]
    if channel:
        conditions.append(SensorReading.channel == channel)

    result = await db.execute(
        select(SensorReading)
        .where(and_(*conditions))
        .order_by(SensorReading.time.desc())
        .limit(limit)
    )
    rows = result.scalars().all()

    return [
        {
            "time": r.time.isoformat(),
            "sensor_id": str(r.sensor_id),
            "channel": r.channel,
            "value": r.value,
            "unit": r.unit,
        }
        for r in reversed(rows)  # return oldest-first for charting
    ]


@router.get("/latest")
async def get_latest(sensor_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Return the most recent reading for each channel of a sensor."""
    from sqlalchemy import text
    result = await db.execute(
        text("""
            SELECT DISTINCT ON (channel)
              time, sensor_id, channel, value, unit
            FROM sensor_readings
            WHERE sensor_id = :sensor_id
            ORDER BY channel, time DESC
        """),
        {"sensor_id": sensor_id},
    )
    rows = result.fetchall()
    return [
        {"time": r.time.isoformat(), "channel": r.channel, "value": r.value, "unit": r.unit}
        for r in rows
    ]
