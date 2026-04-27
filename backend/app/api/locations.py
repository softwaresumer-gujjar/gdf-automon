"""Location CRUD API — /api/locations (admin+)"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user, require_role
from app.models.location import Location
from app.models.user import User

router = APIRouter(prefix="/locations", tags=["locations"])


class LocationCreate(BaseModel):
    name: str
    description: str | None = None
    address: str | None = None


class LocationResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    address: str | None

    class Config:
        from_attributes = True


@router.get("", response_model=list[LocationResponse])
async def list_locations(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """super_admin/admin get all; operators get only their permitted locations."""
    from app.models.user import UserLocationPermission
    if user.role == "super_admin":
        result = await db.execute(select(Location).order_by(Location.name))
        return result.scalars().all()
    if user.role == "admin":
        result = await db.execute(select(Location).order_by(Location.name))
        return result.scalars().all()
    # operator — only permitted locations
    perm = await db.execute(
        select(Location)
        .join(UserLocationPermission, Location.id == UserLocationPermission.location_id)
        .where(UserLocationPermission.user_id == user.id)
        .order_by(Location.name)
    )
    return perm.scalars().all()


@router.post("", response_model=LocationResponse, status_code=201)
async def create_location(
    body: LocationCreate,
    _: User = Depends(require_role("admin", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    loc = Location(**body.model_dump())
    db.add(loc)
    await db.commit()
    await db.refresh(loc)
    return loc


@router.patch("/{location_id}", response_model=LocationResponse)
async def update_location(
    location_id: uuid.UUID,
    body: LocationCreate,
    _: User = Depends(require_role("admin", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    loc = await db.get(Location, location_id)
    if not loc:
        raise HTTPException(404, "Location not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(loc, k, v)
    await db.commit()
    await db.refresh(loc)
    return loc


@router.delete("/{location_id}", status_code=204)
async def delete_location(
    location_id: uuid.UUID,
    _: User = Depends(require_role("super_admin")),
    db: AsyncSession = Depends(get_db),
):
    loc = await db.get(Location, location_id)
    if not loc:
        raise HTTPException(404, "Location not found")
    await db.delete(loc)
    await db.commit()
