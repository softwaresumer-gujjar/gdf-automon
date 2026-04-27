"""Alert rules and active alerts API — /api/alerts"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.alert import AlertRule, ActiveAlert

router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertRuleCreate(BaseModel):
    sensor_id: uuid.UUID
    channel: str
    condition: str  # gt|lt|eq|outside_range
    threshold: float | None = None
    threshold_max: float | None = None
    severity: str = "warning"


@router.get("/rules")
async def list_rules(sensor_id: uuid.UUID | None = None, db: AsyncSession = Depends(get_db)):
    q = select(AlertRule)
    if sensor_id:
        q = q.where(AlertRule.sensor_id == sensor_id)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/rules", status_code=201)
async def create_rule(body: AlertRuleCreate, db: AsyncSession = Depends(get_db)):
    rule = AlertRule(**body.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_rule(rule_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    rule = await db.get(AlertRule, rule_id)
    if rule is None:
        raise HTTPException(404)
    await db.delete(rule)
    await db.commit()


@router.get("/active")
async def list_active_alerts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ActiveAlert).where(ActiveAlert.resolved_at == None).order_by(ActiveAlert.triggered_at.desc())
    )
    return result.scalars().all()
