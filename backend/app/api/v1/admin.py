"""
app/api/v1/admin.py
────────────────────
Admin-only system routes:
  GET  /admin/stats     → System stats (counts, recent activity)
  POST /admin/reindex   → Force re-sync PostgreSQL → ChromaDB + Neo4j
  GET  /admin/health    → Health check all connected services
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, require_admin
from app.models.column import Column
from app.models.history import EditHistory, QueryHistory
from app.models.section import Section
from app.models.table_meta import TableMeta
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["Admin"])


# ── System Stats ──────────────────────────────────────────────────────────────
@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Return high-level system statistics for the admin dashboard."""
    tables_count = (await db.execute(
        select(func.count()).select_from(TableMeta).where(TableMeta.is_active == True)
    )).scalar_one()

    columns_count = (await db.execute(
        select(func.count()).select_from(Column).where(Column.is_active == True)
    )).scalar_one()

    sections_count = (await db.execute(
        select(func.count()).select_from(Section).where(Section.is_active == True)
    )).scalar_one()

    users_count = (await db.execute(
        select(func.count()).select_from(User).where(User.is_active == True)
    )).scalar_one()

    edits_count = (await db.execute(
        select(func.count()).select_from(EditHistory)
    )).scalar_one()

    queries_count = (await db.execute(
        select(func.count()).select_from(QueryHistory)
    )).scalar_one()

    return {
        "active_tables": tables_count,
        "active_columns": columns_count,
        "active_sections": sections_count,
        "active_users": users_count,
        "total_edits_logged": edits_count,
        "total_queries_logged": queries_count,
    }


# ── Health Check ──────────────────────────────────────────────────────────────
@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """
    Check connectivity to all backing services.
    Returns status of: PostgreSQL, ChromaDB, Neo4j, Gemini API.
    """
    health = {}

    # PostgreSQL
    try:
        await db.execute(text("SELECT 1"))
        health["postgresql"] = "ok"
    except Exception as e:
        health["postgresql"] = f"error: {str(e)}"

    # ChromaDB (stub — will connect in Phase 2)
    health["chromadb"] = "not_connected (Phase 2)"

    # Neo4j (stub — will connect in Phase 2)
    health["neo4j"] = "not_connected (Phase 2)"

    # Gemini (stub — will connect in Phase 2)
    health["gemini"] = "not_connected (Phase 2)"

    overall = "ok" if all(v == "ok" or "Phase 2" in v for v in health.values()) else "degraded"
    return {"status": overall, "services": health}


# ── Force Reindex ─────────────────────────────────────────────────────────────
@router.post("/reindex")
async def force_reindex(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger a full re-sync of PostgreSQL data → ChromaDB + Neo4j.
    This is useful after manual DB edits or if the vector/graph indexes
    get out of sync with the source of truth.

    Phase 2: Will call ingestion_service.full_reindex(db).
    """
    # TODO: from app.services.ingestion import IngestionService
    # await IngestionService(db).full_reindex()
    return {
        "status": "queued",
        "message": "Full reindex is not yet wired up (Phase 2). "
                   "Will sync all active tables → ChromaDB + Neo4j.",
    }
