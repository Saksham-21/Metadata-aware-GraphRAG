"""
app/core/dependencies.py
────────────────────────
FastAPI dependency functions injected into route handlers.

Usage in a route:
    @router.get("/...")
    async def my_route(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ):
        ...

Role guards:
    current_user: User = Depends(require_roles(Role.ADMIN, Role.DEVELOPER))
"""

from typing import List
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import Role, decode_access_token
from app.db.postgres import get_session

# Re-export get_db as a friendlier alias used in routes
get_db = get_session

# Bearer token extractor
_bearer = HTTPBearer(auto_error=True)


# ── Token → User ──────────────────────────────────────────────────────────────
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
):
    """
    Validate JWT from Authorization header and return the matching DB user.
    Raises 401 if token is invalid/expired, 404 if user no longer exists,
    403 if user is deactivated.
    """
    # Import here to avoid circular imports (models → db → dependencies)
    from app.models.user import User

    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(credentials.credentials)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Contact an admin.",
        )
    return user


# ── Role guard factory ────────────────────────────────────────────────────────
def require_roles(*allowed_roles: str):
    """
    Returns a dependency that raises 403 if the current user's role
    is not in the provided allowed_roles tuple.

    Example:
        Depends(require_roles(Role.ADMIN))
        Depends(require_roles(Role.ADMIN, Role.DEVELOPER))
    """
    async def _check(
        current_user=Depends(get_current_user),
    ):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Access denied. Required role(s): {', '.join(allowed_roles)}. "
                    f"Your role: {current_user.role}."
                ),
            )
        return current_user

    return _check


# ── Shorthand role dependencies ───────────────────────────────────────────────
# Use these directly in route signatures for clarity.
require_admin        = require_roles(Role.ADMIN)
require_developer    = require_roles(Role.ADMIN, Role.DEVELOPER)
require_ba_or_above  = require_roles(Role.ADMIN, Role.DEVELOPER, Role.BA)
require_any_user     = require_roles(*Role.ALL)
