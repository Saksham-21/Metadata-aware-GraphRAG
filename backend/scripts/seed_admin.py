"""
scripts/seed_admin.py
──────────────────────
Seeds the first admin user into the database.

Usage:
    uv run python scripts/seed_admin.py

You can override defaults with env vars or just edit the constants below.
Safe to run multiple times — skips if the email already exists.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv
# Make sure the app package is importable from the backend root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User, UserRole

load_dotenv()
# ── Seed values (override via env vars if you prefer) ─────────────────────────
ADMIN_NAME     = os.getenv("SEED_ADMIN_NAME",     "Admin User")
ADMIN_EMAIL    = os.getenv("SEED_ADMIN_EMAIL",    "admin@example.com")
ADMIN_PASSWORD = os.getenv("SEED_ADMIN_PASSWORD", "Admin@1234")


async def seed() -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionLocal() as db:
        # Check if admin already exists
        existing = (
            await db.execute(select(User).where(User.email == ADMIN_EMAIL))
        ).scalar_one_or_none()

        if existing:
            print(f"⚠️  Admin '{ADMIN_EMAIL}' already exists — skipping.")
            return

        admin = User(
            name=ADMIN_NAME,
            email=ADMIN_EMAIL,
            password_hash=hash_password(ADMIN_PASSWORD),
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(admin)
        await db.commit()
        await db.refresh(admin)

        print(f"✅  Admin user created!")
        print(f"    ID    : {admin.id}")
        print(f"    Email : {admin.email}")
        print(f"    Role  : {admin.role.value}")
        print(f"    Password: {ADMIN_PASSWORD}  ← change this after first login!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
