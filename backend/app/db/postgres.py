"""
app/db/postgres.py
──────────────────
Async SQLAlchemy engine, session factory, and FastAPI dependency.

All DB access in route handlers should use:
    db: AsyncSession = Depends(get_session)
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# ── Engine ────────────────────────────────────────────────────────────────────
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_DEBUG,       # prints SQL in development
    pool_pre_ping=True,            # reconnects stale connections
    pool_size=10,
    max_overflow=20,
)

# ── Session factory ───────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,        # keeps ORM objects usable after commit
    autoflush=False,
    autocommit=False,
)


# ── Base class for all ORM models ─────────────────────────────────────────────
class Base(DeclarativeBase):
    """
    All SQLAlchemy models inherit from this Base.
    Placed here (not in models/) to avoid circular imports when alembic
    imports models for autogenerate.
    """
    pass


# ── FastAPI dependency ────────────────────────────────────────────────────────
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Yields an AsyncSession per request.
    Automatically commits on success, rolls back on any exception,
    and always closes the session.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
