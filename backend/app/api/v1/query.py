"""
app/api/v1/query.py
────────────────────
Query routes (NL → table/column suggestions + optional SQL):
  POST /query                   → All authenticated — submit NL question
  GET  /query/history           → (see history.py — registered there)
  ...

The actual AI pipeline (ChromaDB → Neo4j → Gemini) lives in
app/services/query_engine.py. This file is the HTTP entry point only.

In Phase 1 (PostgreSQL only), the query engine is a STUB that returns
a placeholder response. Swap in the real engine in Phase 2.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.history import FeedbackType, QueryHistory
from app.models.user import User
from app.schemas.history import QueryRequest, QueryResponse

router = APIRouter(prefix="/query", tags=["Query"])


@router.post("", response_model=QueryResponse)
async def submit_query(
    body: QueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit a natural-language question.

    Pipeline (Phase 2 — will be wired in when ChromaDB/Neo4j/Gemini are ready):
      1. Resolve section filter (by section_id or section_name)
      2. ChromaDB semantic search (section-filtered)
      3. Neo4j graph expansion (cross-section traversal)
      4. Gemini reasoning + SQL generation (if requested)
      5. Save to query_history
      6. Return structured response

    Phase 1: Returns a stub response confirming receipt.
    """
    # ── Phase 1 stub ──────────────────────────────────────────
    # TODO: replace with real query engine call:
    # from app.services.query_engine import QueryEngine
    # result = await QueryEngine(db).run(body, current_user)

    stub_result = {
        "primary_results": [],
        "cross_section_expansions": [],
        "explanation": (
            "Query engine is not yet connected. "
            "ChromaDB + Neo4j + Gemini integration coming in Phase 2."
        ),
    }

    # Save to query history even in stub mode
    qh = QueryHistory(
        user_id=current_user.id,
        question=body.question,
        section_filter=body.section_name,
        result_tables=stub_result,
        generated_sql=None,
        feedback=FeedbackType.NONE,
    )
    db.add(qh)
    await db.flush()

    return QueryResponse(
        query_id=qh.id,
        question=body.question,
        section_filter=body.section_name,
        primary_results=[],
        cross_section_expansions=[],
        suggested_sql=None,
        explanation=stub_result["explanation"],
    )
