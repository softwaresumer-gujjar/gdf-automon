"""
Web Push notification service.
Sends notifications only to users who:
  1. Have permission to see the sensor (RBAC)
  2. Have push_enabled for the matching severity/location/sensor
"""
import json
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger(__name__)


async def _get_permitted_user_ids(sensor_id: uuid.UUID, session: AsyncSession) -> list[uuid.UUID]:
    """
    Return all user IDs allowed to receive notifications for this sensor.
    super_admin users are always included.
    admin/operator users must have a location or sensor permission.
    """
    from app.models.sensor import Sensor
    from app.models.user import User, UserLocationPermission, UserSensorPermission

    # Get sensor's location
    sensor = await session.get(Sensor, sensor_id)
    location_id = sensor.location_id if sensor else None

    # Users with direct sensor permission
    sensor_perm_result = await session.execute(
        select(UserSensorPermission.user_id).where(UserSensorPermission.sensor_id == sensor_id)
    )
    sensor_user_ids = {r for r, in sensor_perm_result.all()}

    # Users with location permission (if sensor has a location)
    location_user_ids: set[uuid.UUID] = set()
    if location_id:
        loc_perm_result = await session.execute(
            select(UserLocationPermission.user_id).where(
                UserLocationPermission.location_id == location_id
            )
        )
        location_user_ids = {r for r, in loc_perm_result.all()}

    # super_admin users always receive notifications
    sa_result = await session.execute(
        select(User.id).where(User.role == "super_admin", User.is_active == True)
    )
    super_admin_ids = {r for r, in sa_result.all()}

    return list(sensor_user_ids | location_user_ids | super_admin_ids)


async def _is_push_enabled(
    user_id: uuid.UUID,
    sensor_id: uuid.UUID,
    location_id: uuid.UUID | None,
    severity: str,
    session: AsyncSession,
) -> bool:
    """
    Check if the user has push enabled for this alert context.
    Preference matching order (most specific wins):
      1. sensor_id + severity match
      2. sensor_id match (any severity)
      3. location_id + severity match
      4. location_id match
      5. severity match (all sensors/locations)
      6. global preference (no filters)
    If no preference row exists → default = enabled.
    """
    from app.models.user import NotificationPreference

    result = await session.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == user_id)
    )
    prefs = result.scalars().all()
    if not prefs:
        return True  # default: all push enabled

    def score(p: NotificationPreference) -> int:
        """Higher = more specific."""
        s = 0
        if p.sensor_id == sensor_id:
            s += 4
        if p.location_id == location_id:
            s += 2
        if p.severity == severity:
            s += 1
        return s

    # Filter to relevant prefs
    relevant = [
        p for p in prefs
        if (p.sensor_id is None or p.sensor_id == sensor_id)
        and (p.location_id is None or p.location_id == location_id)
        and (p.severity is None or p.severity == severity)
    ]
    if not relevant:
        return True  # no applicable rule → default enabled

    best = max(relevant, key=score)
    return best.push_enabled


async def send_alert_notification(
    title: str,
    body: str,
    severity: str,
    sensor_id: uuid.UUID | None = None,
    target_user_ids: list[uuid.UUID] | None = None,
) -> None:
    """
    Send push notification.
    - sensor_id set → RBAC-filter to permitted users with push enabled
    - target_user_ids set → send only to those users (plan actions, task reviews)
    - both None → broadcast to all subscribers
    """
    if not settings.vapid_private_key:
        logger.debug("VAPID keys not configured — skipping push notification")
        return

    from app.core.database import SessionLocal
    from app.models.alert import PushSubscription
    from app.models.sensor import Sensor

    async with SessionLocal() as session:
        if target_user_ids is not None:
            result = await session.execute(
                select(PushSubscription).where(
                    PushSubscription.user_id.in_(target_user_ids)
                )
            )
            subscriptions = result.scalars().all()
        elif sensor_id is None:
            # Broadcast to all (system alerts)
            result = await session.execute(select(PushSubscription))
            subscriptions = result.scalars().all()
        else:
            permitted_user_ids = await _get_permitted_user_ids(sensor_id, session)
            if not permitted_user_ids:
                return

            # Get sensor location for preference matching
            sensor = await session.get(Sensor, sensor_id)
            location_id = sensor.location_id if sensor else None

            # Filter by notification preferences
            eligible_user_ids = []
            for uid in permitted_user_ids:
                if await _is_push_enabled(uid, sensor_id, location_id, severity, session):
                    eligible_user_ids.append(uid)

            if not eligible_user_ids:
                return

            result = await session.execute(
                select(PushSubscription).where(
                    PushSubscription.user_id.in_(eligible_user_ids)
                )
            )
            subscriptions = result.scalars().all()

    if not subscriptions:
        return

    payload = json.dumps({
        "title": title,
        "body": body,
        "icon": "/icons/icon-192.png",
        "badge": "/icons/badge-72.png",
        "data": {"severity": severity, "url": "/alerts"},
    })

    from pywebpush import webpush, WebPushException
    import asyncio

    async def _send_one(sub: PushSubscription) -> None:
        try:
            await asyncio.to_thread(
                webpush,
                subscription_info={"endpoint": sub.endpoint, "keys": {"p256dh": sub.p256dh, "auth": sub.auth}},
                data=payload,
                vapid_private_key=settings.vapid_private_key,
                vapid_claims={"sub": f"mailto:{settings.vapid_email}"},
            )
        except WebPushException as e:
            if e.response and e.response.status_code in (404, 410):
                async with SessionLocal() as s:
                    s_sub = await s.get(PushSubscription, sub.id)
                    if s_sub:
                        await s.delete(s_sub)
                        await s.commit()
            else:
                logger.error("Web Push failed for %s: %s", sub.endpoint[:50], e)

    await asyncio.gather(*[_send_one(sub) for sub in subscriptions])
