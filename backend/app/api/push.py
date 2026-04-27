"""Web Push subscription management — /api/push"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.alert import PushSubscription
from app.models.user import User

router = APIRouter(prefix="/push", tags=["push"])


class PushSubscriptionPayload(BaseModel):
    endpoint: str
    keys: dict  # {"p256dh": "...", "auth": "..."}


@router.get("/vapid-public-key")
async def get_vapid_public_key():
    if not settings.vapid_public_key:
        raise HTTPException(503, "Web Push not configured on this server")
    return {"publicKey": settings.vapid_public_key}


@router.post("/subscribe", status_code=201)
async def subscribe(
    body: PushSubscriptionPayload,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PushSubscription).where(PushSubscription.endpoint == body.endpoint)
    )
    existing = result.scalar_one_or_none()
    if existing:
        # Update user_id if missing (re-subscribe from same device after login)
        if existing.user_id is None:
            existing.user_id = user.id
            await db.commit()
        return {"status": "already_subscribed"}

    sub = PushSubscription(
        endpoint=body.endpoint,
        p256dh=body.keys.get("p256dh", ""),
        auth=body.keys.get("auth", ""),
        user_id=user.id,
    )
    db.add(sub)
    await db.commit()
    return {"status": "subscribed"}


@router.delete("/unsubscribe")
async def unsubscribe(
    endpoint: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PushSubscription).where(
            PushSubscription.endpoint == endpoint,
            PushSubscription.user_id == user.id,
        )
    )
    sub = result.scalar_one_or_none()
    if sub:
        await db.delete(sub)
        await db.commit()
    return {"status": "unsubscribed"}
