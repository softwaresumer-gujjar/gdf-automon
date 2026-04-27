"""Authentication API — /api/auth/"""
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import (
    hash_password, verify_password, create_access_token, get_current_user,
)
from app.models.user import User
from app.models.auth_token import PasswordResetToken

router = APIRouter(prefix="/auth", tags=["auth"])

RESET_TOKEN_EXPIRE_HOURS = 1


# ── Schemas ───────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("full_name")
    @classmethod
    def full_name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Full name cannot be empty")
        return v.strip()


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True


TokenResponse.model_rebuild()


# ── Register ──────────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "An account with this email already exists")

    user = User(
        email=body.email,
        full_name=body.full_name,
        password_hash=hash_password(body.password),
        role="operator",  # self-registration always creates operator
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Send welcome email (non-blocking)
    import asyncio
    from app.services.email_service import send_welcome_email
    asyncio.create_task(send_welcome_email(user.email, user.full_name))

    token = create_access_token(str(user.id), user.role)
    return {"access_token": token, "token_type": "bearer", "user": user}


# ── Login ─────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == form.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(403, "Your account has been disabled. Contact an administrator.")

    token = create_access_token(str(user.id), user.role)
    return {"access_token": token, "token_type": "bearer", "user": user}


# ── Logout (client removes token; endpoint for audit / future blacklist) ──────

@router.post("/logout")
async def logout(user: User = Depends(get_current_user)):
    # Token invalidation is client-side (remove from localStorage).
    # This endpoint exists for audit logging and future Redis blacklist support.
    return {"status": "logged out", "user_id": str(user.id)}


# ── Me ────────────────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user


# ── Change password (authenticated) ──────────────────────────────────────────

@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    user.password_hash = hash_password(body.new_password)
    await db.commit()
    return {"status": "password updated"}


# ── Forgot password (unauthenticated) ────────────────────────────────────────

@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Always returns 200 even if email not found — prevents user enumeration.
    """
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user and user.is_active:
        # Invalidate any existing unused tokens for this user
        existing = await db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used == False,
            )
        )
        for tok in existing.scalars().all():
            tok.used = True

        # Generate new token
        raw_token = secrets.token_urlsafe(48)
        expires = datetime.now(timezone.utc) + timedelta(hours=RESET_TOKEN_EXPIRE_HOURS)
        prt = PasswordResetToken(token=raw_token, user_id=user.id, expires_at=expires)
        db.add(prt)
        await db.commit()

        # Send reset email (non-blocking)
        import asyncio
        from app.services.email_service import send_password_reset_email
        asyncio.create_task(send_password_reset_email(user.email, user.full_name, raw_token))

    return {"status": "If that email is registered you will receive a reset link shortly."}


# ── Reset password (unauthenticated) ─────────────────────────────────────────

@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token == body.token)
    )
    prt = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if (
        not prt
        or prt.used
        or prt.expires_at.replace(tzinfo=timezone.utc) < now
    ):
        raise HTTPException(400, "This reset link is invalid or has expired. Please request a new one.")

    user = await db.get(User, prt.user_id)
    if not user or not user.is_active:
        raise HTTPException(400, "Account not found or disabled.")

    user.password_hash = hash_password(body.new_password)
    prt.used = True
    await db.commit()

    return {"status": "Password updated successfully. You can now sign in."}


# ── Validate reset token (check before showing the form) ─────────────────────

@router.get("/reset-password/validate")
async def validate_reset_token(token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token == token)
    )
    prt = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    valid = (
        prt is not None
        and not prt.used
        and prt.expires_at.replace(tzinfo=timezone.utc) >= now
    )
    return {"valid": valid}
