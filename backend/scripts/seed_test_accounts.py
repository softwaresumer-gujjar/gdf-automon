"""
Seed test accounts into the database.
Run from the backend/ directory:
    python scripts/seed_test_accounts.py

Test credentials created:
    super_admin  super@gdf.local      SuperAdmin@123
    admin        admin@gdf.local      Admin@123456
    operator     operator@gdf.local   Operator@123
"""
import asyncio
import sys
import os

# Make sure app package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.core.config import settings
from app.core.auth import hash_password
from app.models.user import User

ACCOUNTS = [
    {
        "email": "super@gdf.local",
        "full_name": "Super Administrator",
        "password": "SuperAdmin@123",
        "role": "super_admin",
    },
    {
        "email": "admin@gdf.local",
        "full_name": "Farm Administrator",
        "password": "Admin@123456",
        "role": "admin",
    },
    {
        "email": "operator@gdf.local",
        "full_name": "Farm Operator",
        "password": "Operator@123",
        "role": "operator",
    },
]


async def seed():
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        for acct in ACCOUNTS:
            result = await db.execute(select(User).where(User.email == acct["email"]))
            existing = result.scalars().first()
            if existing:
                print(f"  [skip] {acct['email']} already exists (role={existing.role})")
                continue
            user = User(
                email=acct["email"],
                full_name=acct["full_name"],
                password_hash=hash_password(acct["password"]),
                role=acct["role"],
                is_active=True,
            )
            db.add(user)
            print(f"  [+] {acct['role']:12s}  {acct['email']}  /  {acct['password']}")
        await db.commit()

    await engine.dispose()
    print("\nDone. Run 'alembic upgrade head' first if you haven't already.")


if __name__ == "__main__":
    asyncio.run(seed())
