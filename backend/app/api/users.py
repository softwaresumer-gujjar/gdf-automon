"""User management API — /api/users (super_admin only for most ops)"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user, require_role, hash_password
from app.models.user import User, UserLocationPermission, UserSensorPermission, ROLES

router = APIRouter(prefix="/users", tags=["users"])


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: str = "operator"


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: str | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class PermissionSet(BaseModel):
    location_ids: list[uuid.UUID] = []
    sensor_ids: list[uuid.UUID] = []


class PermissionResponse(BaseModel):
    location_ids: list[uuid.UUID]
    sensor_ids: list[uuid.UUID]


# ── User CRUD ────────────────────────────────────────────────────────────────

@router.get("", response_model=list[UserResponse])
async def list_users(
    _: User = Depends(require_role("admin", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).order_by(User.full_name))
    return result.scalars().all()


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    body: UserCreate,
    _: User = Depends(require_role("super_admin")),
    db: AsyncSession = Depends(get_db),
):
    if body.role not in ROLES:
        raise HTTPException(400, f"Invalid role. Must be one of: {ROLES}")
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Email already registered")
    user = User(
        email=body.email,
        full_name=body.full_name,
        password_hash=hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    caller: User = Depends(require_role("admin", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    caller: User = Depends(require_role("super_admin")),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    if body.role is not None and body.role not in ROLES:
        raise HTTPException(400, f"Invalid role. Must be one of: {ROLES}")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(user, k, v)
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: uuid.UUID,
    caller: User = Depends(require_role("super_admin")),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    if user.id == caller.id:
        raise HTTPException(400, "Cannot delete your own account")
    await db.delete(user)
    await db.commit()


# ── Permission management ────────────────────────────────────────────────────

@router.get("/{user_id}/permissions", response_model=PermissionResponse)
async def get_permissions(
    user_id: uuid.UUID,
    caller: User = Depends(require_role("admin", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    loc_result = await db.execute(
        select(UserLocationPermission.location_id).where(
            UserLocationPermission.user_id == user_id
        )
    )
    sensor_result = await db.execute(
        select(UserSensorPermission.sensor_id).where(
            UserSensorPermission.user_id == user_id
        )
    )
    return {
        "location_ids": [r for r, in loc_result.all()],
        "sensor_ids": [r for r, in sensor_result.all()],
    }


@router.put("/{user_id}/permissions")
async def set_permissions(
    user_id: uuid.UUID,
    body: PermissionSet,
    caller: User = Depends(require_role("super_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Replace all location + sensor permissions for a user (super_admin only)."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    # Clear existing
    await db.execute(
        delete(UserLocationPermission).where(UserLocationPermission.user_id == user_id)
    )
    await db.execute(
        delete(UserSensorPermission).where(UserSensorPermission.user_id == user_id)
    )

    # Insert new
    for loc_id in body.location_ids:
        db.add(UserLocationPermission(user_id=user_id, location_id=loc_id))
    for sensor_id in body.sensor_ids:
        db.add(UserSensorPermission(user_id=user_id, sensor_id=sensor_id))

    await db.commit()
    return {"status": "permissions updated"}


@router.post("/{user_id}/permissions/locations/{location_id}", status_code=201)
async def add_location_permission(
    user_id: uuid.UUID,
    location_id: uuid.UUID,
    _: User = Depends(require_role("super_admin")),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    existing = await db.execute(
        select(UserLocationPermission).where(
            UserLocationPermission.user_id == user_id,
            UserLocationPermission.location_id == location_id,
        )
    )
    if not existing.scalar_one_or_none():
        db.add(UserLocationPermission(user_id=user_id, location_id=location_id))
        await db.commit()
    return {"status": "ok"}


@router.delete("/{user_id}/permissions/locations/{location_id}", status_code=204)
async def remove_location_permission(
    user_id: uuid.UUID,
    location_id: uuid.UUID,
    _: User = Depends(require_role("super_admin")),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        delete(UserLocationPermission).where(
            UserLocationPermission.user_id == user_id,
            UserLocationPermission.location_id == location_id,
        )
    )
    await db.commit()


@router.post("/{user_id}/permissions/sensors/{sensor_id}", status_code=201)
async def add_sensor_permission(
    user_id: uuid.UUID,
    sensor_id: uuid.UUID,
    _: User = Depends(require_role("super_admin")),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    existing = await db.execute(
        select(UserSensorPermission).where(
            UserSensorPermission.user_id == user_id,
            UserSensorPermission.sensor_id == sensor_id,
        )
    )
    if not existing.scalar_one_or_none():
        db.add(UserSensorPermission(user_id=user_id, sensor_id=sensor_id))
        await db.commit()
    return {"status": "ok"}


@router.delete("/{user_id}/permissions/sensors/{sensor_id}", status_code=204)
async def remove_sensor_permission(
    user_id: uuid.UUID,
    sensor_id: uuid.UUID,
    _: User = Depends(require_role("super_admin")),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        delete(UserSensorPermission).where(
            UserSensorPermission.user_id == user_id,
            UserSensorPermission.sensor_id == sensor_id,
        )
    )
    await db.commit()
