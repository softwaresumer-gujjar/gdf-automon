"""Notification preferences API — /api/notifications/preferences"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user, require_role
from app.models.user import NotificationPreference, User

router = APIRouter(prefix="/notifications", tags=["notifications"])

SEVERITIES = ("info", "warning", "critical")


class PreferenceCreate(BaseModel):
    severity: str | None = None        # None = applies to all
    location_id: uuid.UUID | None = None
    sensor_id: uuid.UUID | None = None
    push_enabled: bool = True


class PreferenceResponse(BaseModel):
    id: uuid.UUID
    severity: str | None
    location_id: uuid.UUID | None
    sensor_id: uuid.UUID | None
    push_enabled: bool

    class Config:
        from_attributes = True


def _check_severity(severity: str | None) -> None:
    if severity is not None and severity not in SEVERITIES:
        raise HTTPException(400, f"severity must be one of {SEVERITIES}")


@router.get("/preferences", response_model=list[PreferenceResponse])
async def list_preferences(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the calling user's own preferences."""
    result = await db.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == user.id)
    )
    return result.scalars().all()


@router.get("/preferences/users/{user_id}", response_model=list[PreferenceResponse])
async def list_user_preferences(
    user_id: uuid.UUID,
    _: User = Depends(require_role("admin", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Admin/super_admin: read any user's preferences."""
    result = await db.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == user_id)
    )
    return result.scalars().all()


@router.post("/preferences", response_model=PreferenceResponse, status_code=201)
async def create_preference(
    body: PreferenceCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _check_severity(body.severity)
    pref = NotificationPreference(user_id=user.id, **body.model_dump())
    db.add(pref)
    await db.commit()
    await db.refresh(pref)
    return pref


@router.patch("/preferences/{pref_id}", response_model=PreferenceResponse)
async def update_preference(
    pref_id: uuid.UUID,
    body: PreferenceCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pref = await db.get(NotificationPreference, pref_id)
    if not pref or pref.user_id != user.id:
        raise HTTPException(404, "Preference not found")
    _check_severity(body.severity)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(pref, k, v)
    await db.commit()
    await db.refresh(pref)
    return pref


@router.delete("/preferences/{pref_id}", status_code=204)
async def delete_preference(
    pref_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pref = await db.get(NotificationPreference, pref_id)
    if not pref or pref.user_id != user.id:
        raise HTTPException(404, "Preference not found")
    await db.delete(pref)
    await db.commit()


@router.put("/preferences/reset")
async def reset_preferences(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete all of the calling user's preferences (restore to defaults)."""
    await db.execute(
        delete(NotificationPreference).where(NotificationPreference.user_id == user.id)
    )
    await db.commit()
    return {"status": "preferences reset"}
