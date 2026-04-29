"""Alert rules and active alerts API — /api/alerts"""
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user, require_role
from app.models.alert import AlertRule, ActiveAlert, AlertRuleAction
from app.models.user import User

router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertRuleCreate(BaseModel):
    sensor_id: uuid.UUID
    channel: str
    condition: str  # gt|lt|eq|outside_range
    threshold: float | None = None
    threshold_max: float | None = None
    severity: str = "warning"


class AlertRuleUpdate(BaseModel):
    enabled: bool | None = None
    severity: str | None = None
    threshold: float | None = None
    threshold_max: float | None = None


class AlertRuleActionCreate(BaseModel):
    action_type: str  # email|sms|whatsapp|call|notification|reminder
    config: dict[str, Any] = {}
    enabled: bool = True


class AlertRuleActionResponse(BaseModel):
    id: uuid.UUID
    rule_id: uuid.UUID
    action_type: str
    config: dict[str, Any]
    enabled: bool

    class Config:
        from_attributes = True


# ── Rules ─────────────────────────────────────────────────────────────────────

@router.get("/rules")
async def list_rules(sensor_id: uuid.UUID | None = None, db: AsyncSession = Depends(get_db)):
    q = select(AlertRule)
    if sensor_id:
        q = q.where(AlertRule.sensor_id == sensor_id)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/rules", status_code=201)
async def create_rule(
    body: AlertRuleCreate,
    _: User = Depends(require_role("admin", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    rule = AlertRule(**body.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.patch("/rules/{rule_id}")
async def update_rule(
    rule_id: uuid.UUID,
    body: AlertRuleUpdate,
    _: User = Depends(require_role("admin", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    rule = await db.get(AlertRule, rule_id)
    if rule is None:
        raise HTTPException(404, "Rule not found")
    for key, val in body.model_dump(exclude_none=True).items():
        setattr(rule, key, val)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_rule(
    rule_id: uuid.UUID,
    _: User = Depends(require_role("admin", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    rule = await db.get(AlertRule, rule_id)
    if rule is None:
        raise HTTPException(404)
    await db.delete(rule)
    await db.commit()


# ── Rule Actions ──────────────────────────────────────────────────────────────

@router.get("/rules/{rule_id}/actions", response_model=list[AlertRuleActionResponse])
async def list_rule_actions(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AlertRuleAction).where(AlertRuleAction.rule_id == rule_id)
    )
    return result.scalars().all()


@router.post("/rules/{rule_id}/actions", response_model=AlertRuleActionResponse, status_code=201)
async def add_rule_action(
    rule_id: uuid.UUID,
    body: AlertRuleActionCreate,
    _: User = Depends(require_role("admin", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    rule = await db.get(AlertRule, rule_id)
    if rule is None:
        raise HTTPException(404, "Rule not found")
    action = AlertRuleAction(rule_id=rule_id, **body.model_dump())
    db.add(action)
    await db.commit()
    await db.refresh(action)
    return action


@router.patch("/rules/{rule_id}/actions/{action_id}", response_model=AlertRuleActionResponse)
async def update_rule_action(
    rule_id: uuid.UUID,
    action_id: uuid.UUID,
    body: AlertRuleActionCreate,
    _: User = Depends(require_role("admin", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    action = await db.get(AlertRuleAction, action_id)
    if action is None or action.rule_id != rule_id:
        raise HTTPException(404, "Action not found")
    for key, val in body.model_dump(exclude_none=True).items():
        setattr(action, key, val)
    await db.commit()
    await db.refresh(action)
    return action


@router.delete("/rules/{rule_id}/actions/{action_id}", status_code=204)
async def delete_rule_action(
    rule_id: uuid.UUID,
    action_id: uuid.UUID,
    _: User = Depends(require_role("admin", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    action = await db.get(AlertRuleAction, action_id)
    if action is None or action.rule_id != rule_id:
        raise HTTPException(404, "Action not found")
    await db.delete(action)
    await db.commit()


# ── Active Alerts ─────────────────────────────────────────────────────────────

@router.get("/active")
async def list_active_alerts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ActiveAlert).where(ActiveAlert.resolved_at == None).order_by(ActiveAlert.triggered_at.desc())
    )
    return result.scalars().all()
