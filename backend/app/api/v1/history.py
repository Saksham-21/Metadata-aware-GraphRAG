"""
app/api/v1/history.py
──────────────────────
Global edit history routes (read-only audit trail):
  GET /history         → All authenticated — paginated list of all edits
  GET /history/{id}    → All authenticated — single history entry (before/after diff)

Query history routes (per-user private):
  GET    /query/history           → Current user's own query history
  GET    /query/history/{id}      → Single past query
  PATCH  /query/history/{id}/feedback → Submit thumbs-up / thumbs-down
  DELETE /query/history           → Clear current user's query history
"""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.core.security import Role
from app.models.history import ActionType, EditHistory, EntityType, FeedbackType, QueryHistory
from app.models.user import User
from app.schemas.history import (
    EditHistoryListResponse,
    EditHistoryResponse,
    FeedbackRequest,
    QueryHistoryListResponse,
    QueryHistoryResponse,
)

router = APIRouter(tags=["History"])


# ─────────────────────────────────────────────────────────────────────────────
# EDIT HISTORY  (GLOBAL scope)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/history", response_model=EditHistoryListResponse)
async def list_edit_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    entity_type: Optional[EntityType] = Query(None),
    entity_id: Optional[uuid.UUID] = Query(None),
    action: Optional[ActionType] = Query(None),
    changed_by_user_id: Optional[uuid.UUID] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    Paginated, filterable global edit history.
    All authenticated users can view. Admin sees everything;
    others see the same records but could be restricted further if needed.
    """
    query = select(EditHistory)

    if entity_type:
        query = query.where(EditHistory.entity_type == entity_type)
    if entity_id:
        query = query.where(EditHistory.entity_id == entity_id)
    if action:
        query = query.where(EditHistory.action == action)
    if changed_by_user_id:
        query = query.where(EditHistory.changed_by == changed_by_user_id)
    if from_date:
        query = query.where(EditHistory.changed_at >= from_date)
    if to_date:
        query = query.where(EditHistory.changed_at <= to_date)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    offset = (page - 1) * page_size
    items = (await db.execute(
        query.order_by(EditHistory.changed_at.desc()).offset(offset).limit(page_size)
    )).scalars().all()

    # Denormalise user name
    user_cache: dict[uuid.UUID, str] = {}
    response_items = []
    for h in items:
        user_name = None
        if h.changed_by:
            if h.changed_by not in user_cache:
                u = await db.get(User, h.changed_by)
                user_cache[h.changed_by] = u.name if u else "Unknown"
            user_name = user_cache[h.changed_by]
        item = EditHistoryResponse.model_validate(h)
        item.changed_by_name = user_name
        response_items.append(item)

    return EditHistoryListResponse(total=total, page=page, page_size=page_size, items=response_items)


@router.get("/history/{history_id}", response_model=EditHistoryResponse)
async def get_edit_history(
    history_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Return a single history entry showing before/after state."""
    h = await db.get(EditHistory, history_id)
    if not h:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="History entry not found.")
    item = EditHistoryResponse.model_validate(h)
    if h.changed_by:
        u = await db.get(User, h.changed_by)
        item.changed_by_name = u.name if u else "Unknown"
    return item


# ─────────────────────────────────────────────────────────────────────────────
# QUERY HISTORY  (PER-USER scope)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/query/history", response_model=QueryHistoryListResponse)
async def list_query_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Return the current user's own query history. Private."""
    query = select(QueryHistory).where(QueryHistory.user_id == current_user.id)
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    offset = (page - 1) * page_size
    items = (await db.execute(
        query.order_by(QueryHistory.created_at.desc()).offset(offset).limit(page_size)
    )).scalars().all()
    return QueryHistoryListResponse(total=total, page=page, page_size=page_size, items=list(items))


@router.get("/query/history/{query_id}", response_model=QueryHistoryResponse)
async def get_query_history(
    query_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return a single past query. Users can only see their own records."""
    qh = await db.get(QueryHistory, query_id)
    if not qh:
        raise HTTPException(status_code=404, detail="Query history not found.")
    # Only the owner (or admin) can view
    if qh.user_id != current_user.id and current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Access denied.")
    return qh


@router.patch("/query/history/{query_id}/feedback", response_model=QueryHistoryResponse)
async def submit_feedback(
    query_id: uuid.UUID,
    body: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit positive/negative feedback on a past query result."""
    qh = await db.get(QueryHistory, query_id)
    if not qh:
        raise HTTPException(status_code=404, detail="Query history not found.")
    if qh.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only rate your own queries.")
    qh.feedback = body.feedback
    await db.flush()
    return qh


@router.delete("/query/history", status_code=status.HTTP_204_NO_CONTENT)
async def clear_query_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete ALL query history for the current user."""
    from sqlalchemy import delete as sql_delete
    await db.execute(
        sql_delete(QueryHistory).where(QueryHistory.user_id == current_user.id)
    )
    return None
