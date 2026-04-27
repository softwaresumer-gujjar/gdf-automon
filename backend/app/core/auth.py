"""
JWT authentication core.
- Passwords hashed with bcrypt via passlib
- Tokens: HS256 JWT, 24h expiry (configurable)
- FastAPI Depends: get_current_user, require_role
- RBAC helper: get_permitted_sensor_ids(user, db)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User, UserLocationPermission, UserSensorPermission
from app.models.sensor import Sensor

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24


# ── Password helpers ────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return _pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── JWT helpers ──────────────────────────────────────────────────────────────

def create_access_token(user_id: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode(
        {"sub": user_id, "role": role, "exp": expire},
        settings.secret_key,
        algorithm=ALGORITHM,
    )


# ── FastAPI dependencies ─────────────────────────────────────────────────────

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if not user_id:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    user = await db.get(User, uuid.UUID(user_id))
    if user is None or not user.is_active:
        raise credentials_exc
    return user


def require_role(*roles: str):
    """Dependency factory: raise 403 if user's role is not in `roles`."""
    async def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
        return user
    return _check


# ── RBAC helpers ─────────────────────────────────────────────────────────────

async def get_permitted_sensor_ids(user: User, db: AsyncSession) -> list[uuid.UUID] | None:
    """
    Returns the list of sensor UUIDs this user may access.
    Returns None for super_admin (meaning: all sensors).

    Logic:
      super_admin → None (unrestricted)
      admin       → all sensors whose location_id is in user's location permissions
      operator    → sensors in permitted locations PLUS individually granted sensors
    """
    if user.role == "super_admin":
        return None  # no filter

    # Locations this user is allowed
    loc_result = await db.execute(
        select(UserLocationPermission.location_id).where(
            UserLocationPermission.user_id == user.id
        )
    )
    allowed_location_ids = [r for r, in loc_result.all()]

    # Sensors in those locations
    sensor_result = await db.execute(
        select(Sensor.id).where(Sensor.location_id.in_(allowed_location_ids))
    )
    sensor_ids = {r for r, in sensor_result.all()}

    # Add individually granted sensors (operator-level granular override)
    override_result = await db.execute(
        select(UserSensorPermission.sensor_id).where(
            UserSensorPermission.user_id == user.id
        )
    )
    sensor_ids.update(r for r, in override_result.all())

    return list(sensor_ids)


async def assert_sensor_access(
    sensor_id: uuid.UUID, user: User, db: AsyncSession
) -> None:
    """Raise 404 (not 403 — avoids info leak) if user can't access this sensor."""
    permitted = await get_permitted_sensor_ids(user, db)
    if permitted is not None and sensor_id not in permitted:
        raise HTTPException(404, "Sensor not found")
