"""Sensor CRUD API — /api/sensors"""
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user, require_role, get_permitted_sensor_ids, assert_sensor_access
from app.models.sensor import Sensor
from app.models.user import User
from app.plugins.registry import registry

router = APIRouter(prefix="/sensors", tags=["sensors"])


class SensorCreate(BaseModel):
    name: str
    sensor_type: str
    protocol: str
    config: dict[str, Any] = {}
    location_id: uuid.UUID | None = None
    description: str | None = None


class SensorUpdate(BaseModel):
    name: str | None = None
    config: dict[str, Any] | None = None
    location_id: uuid.UUID | None = None
    description: str | None = None
    status: str | None = None


class SensorResponse(BaseModel):
    id: uuid.UUID
    name: str
    sensor_type: str
    protocol: str
    config: dict[str, Any]
    status: str
    location_id: uuid.UUID | None
    description: str | None

    class Config:
        from_attributes = True


@router.get("/types")
async def list_sensor_types(_: User = Depends(get_current_user)):
    """Return all registered sensor types with their config schemas."""
    return registry.all_types()


@router.get("", response_model=list[SensorResponse])
async def list_sensors(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    permitted = await get_permitted_sensor_ids(user, db)
    query = select(Sensor).order_by(Sensor.created_at)
    if permitted is not None:
        query = query.where(Sensor.id.in_(permitted))
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=SensorResponse, status_code=201)
async def create_sensor(
    body: SensorCreate,
    _: User = Depends(require_role("admin", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    if registry.get(body.sensor_type) is None:
        raise HTTPException(400, f"Unknown sensor_type: {body.sensor_type!r}")
    sensor = Sensor(**body.model_dump())
    db.add(sensor)
    await db.commit()
    await db.refresh(sensor)
    return sensor


@router.get("/{sensor_id}", response_model=SensorResponse)
async def get_sensor(
    sensor_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await assert_sensor_access(sensor_id, user, db)
    sensor = await db.get(Sensor, sensor_id)
    if sensor is None:
        raise HTTPException(404, "Sensor not found")
    return sensor


@router.patch("/{sensor_id}", response_model=SensorResponse)
async def update_sensor(
    sensor_id: uuid.UUID,
    body: SensorUpdate,
    user: User = Depends(require_role("admin", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    await assert_sensor_access(sensor_id, user, db)
    sensor = await db.get(Sensor, sensor_id)
    if sensor is None:
        raise HTTPException(404, "Sensor not found")
    for key, val in body.model_dump(exclude_none=True).items():
        setattr(sensor, key, val)
    await db.commit()
    await db.refresh(sensor)
    return sensor


@router.delete("/{sensor_id}", status_code=204)
async def delete_sensor(
    sensor_id: uuid.UUID,
    _: User = Depends(require_role("super_admin")),
    db: AsyncSession = Depends(get_db),
):
    sensor = await db.get(Sensor, sensor_id)
    if sensor is None:
        raise HTTPException(404, "Sensor not found")
    await db.delete(sensor)
    await db.commit()


@router.post("/{sensor_id}/pause", response_model=SensorResponse)
async def pause_sensor(
    sensor_id: uuid.UUID,
    user: User = Depends(require_role("admin", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    await assert_sensor_access(sensor_id, user, db)
    sensor = await db.get(Sensor, sensor_id)
    if sensor is None:
        raise HTTPException(404, "Sensor not found")
    sensor.status = "paused"
    await db.commit()
    await db.refresh(sensor)
    return sensor


@router.post("/{sensor_id}/resume", response_model=SensorResponse)
async def resume_sensor(
    sensor_id: uuid.UUID,
    user: User = Depends(require_role("admin", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    await assert_sensor_access(sensor_id, user, db)
    sensor = await db.get(Sensor, sensor_id)
    if sensor is None:
        raise HTTPException(404, "Sensor not found")
    sensor.status = "active"
    await db.commit()
    await db.refresh(sensor)
    return sensor


@router.post("/{sensor_id}/test")
async def test_sensor_connection(
    sensor_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await assert_sensor_access(sensor_id, user, db)
    sensor = await db.get(Sensor, sensor_id)
    if sensor is None:
        raise HTTPException(404, "Sensor not found")
    adapter = registry.create(sensor.sensor_type, str(sensor.id), sensor.config)
    ok, message = await adapter.test_connection()
    return {"ok": ok, "message": message}
