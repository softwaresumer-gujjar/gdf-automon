"""Planning API — /api/plans (admin+ to write, all authenticated to read own)"""
import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user, require_role, assert_sensor_access
from app.models.plan import Plan, PlanAction
from app.models.user import User

router = APIRouter(prefix="/plans", tags=["plans"])

ACTION_TYPES = ("notification", "sms", "call", "reminder")
TRIGGER_ON = ("above_upper", "below_lower", "outside_range", "any_breach")


# ── Schemas ───────────────────────────────────────────────────────────────────

class PlanCreate(BaseModel):
    name: str
    description: str | None = None
    sensor_id: uuid.UUID
    channel: str
    target_value: float
    target_unit: str | None = None
    lower_limit: float | None = None
    upper_limit: float | None = None
    enabled: bool = True


class PlanUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    target_value: float | None = None
    target_unit: str | None = None
    lower_limit: float | None = None
    upper_limit: float | None = None
    enabled: bool | None = None


class PlanResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    sensor_id: uuid.UUID
    channel: str
    target_value: float
    target_unit: str | None
    lower_limit: float | None
    upper_limit: float | None
    enabled: bool

    class Config:
        from_attributes = True


class PlanActionCreate(BaseModel):
    action_type: str
    trigger_on: str = "any_breach"
    message_template: str = "Sensor {sensor} {channel}: {value} breached target {target}"
    recipient_user_ids: list[uuid.UUID] | None = None
    config: dict[str, Any] = {}
    enabled: bool = True


class PlanActionResponse(BaseModel):
    id: uuid.UUID
    plan_id: uuid.UUID
    action_type: str
    trigger_on: str
    message_template: str
    recipient_user_ids: list[uuid.UUID] | None
    config: dict[str, Any]
    enabled: bool

    class Config:
        from_attributes = True


# ── Plan CRUD ─────────────────────────────────────────────────────────────────

@router.get("", response_model=list[PlanResponse])
async def list_plans(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Plan).order_by(Plan.created_at))
    return result.scalars().all()


@router.post("", response_model=PlanResponse, status_code=201)
async def create_plan(
    body: PlanCreate,
    user: User = Depends(require_role("admin", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    await assert_sensor_access(body.sensor_id, user, db)
    plan = Plan(**body.model_dump(), created_by_id=user.id)
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(
    plan_id: uuid.UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    plan = await db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    return plan


@router.patch("/{plan_id}", response_model=PlanResponse)
async def update_plan(
    plan_id: uuid.UUID,
    body: PlanUpdate,
    _: User = Depends(require_role("admin", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    plan = await db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(plan, k, v)
    await db.commit()
    await db.refresh(plan)
    return plan


@router.delete("/{plan_id}", status_code=204)
async def delete_plan(
    plan_id: uuid.UUID,
    _: User = Depends(require_role("super_admin")),
    db: AsyncSession = Depends(get_db),
):
    plan = await db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    await db.delete(plan)
    await db.commit()


# ── Plan Actions ──────────────────────────────────────────────────────────────

@router.get("/{plan_id}/actions", response_model=list[PlanActionResponse])
async def list_actions(
    plan_id: uuid.UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PlanAction).where(PlanAction.plan_id == plan_id).order_by(PlanAction.created_at)
    )
    return result.scalars().all()


@router.post("/{plan_id}/actions", response_model=PlanActionResponse, status_code=201)
async def create_action(
    plan_id: uuid.UUID,
    body: PlanActionCreate,
    _: User = Depends(require_role("admin", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    if body.action_type not in ACTION_TYPES:
        raise HTTPException(400, f"action_type must be one of {ACTION_TYPES}")
    if body.trigger_on not in TRIGGER_ON:
        raise HTTPException(400, f"trigger_on must be one of {TRIGGER_ON}")
    plan = await db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    action = PlanAction(
        plan_id=plan_id,
        **body.model_dump(),
    )
    db.add(action)
    await db.commit()
    await db.refresh(action)
    return action


@router.patch("/{plan_id}/actions/{action_id}", response_model=PlanActionResponse)
async def update_action(
    plan_id: uuid.UUID,
    action_id: uuid.UUID,
    body: PlanActionCreate,
    _: User = Depends(require_role("admin", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    action = await db.get(PlanAction, action_id)
    if not action or action.plan_id != plan_id:
        raise HTTPException(404, "Action not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(action, k, v)
    await db.commit()
    await db.refresh(action)
    return action


@router.delete("/{plan_id}/actions/{action_id}", status_code=204)
async def delete_action(
    plan_id: uuid.UUID,
    action_id: uuid.UUID,
    _: User = Depends(require_role("admin", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    action = await db.get(PlanAction, action_id)
    if not action or action.plan_id != plan_id:
        raise HTTPException(404, "Action not found")
    await db.delete(action)
    await db.commit()
