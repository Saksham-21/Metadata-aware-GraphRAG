"""
app/schemas/history.py
──────────────────────
Pydantic schemas for EditHistory and QueryHistory.
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel

from app.models.history import ActionType, EntityType, FeedbackType


# ── Edit History ──────────────────────────────────────────────────────────────
class EditHistoryResponse(BaseModel):
    id: uuid.UUID
    entity_type: EntityType
    entity_id: uuid.UUID
    entity_name: Optional[str] = None
    action: ActionType
    changed_by: Optional[uuid.UUID] = None
    changed_by_name: Optional[str] = None   # denormalised from User join
    changed_at: datetime
    before_state: Optional[dict[str, Any]] = None
    after_state: Optional[dict[str, Any]] = None
    change_summary: Optional[str] = None

    model_config = {"from_attributes": True}


class EditHistoryListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[EditHistoryResponse]


# ── Query History ─────────────────────────────────────────────────────────────
class QueryRequest(BaseModel):
    question: str
    section_id: Optional[uuid.UUID] = None    # filter to a specific section
    section_name: Optional[str] = None         # alternative: pass section slug
    include_sql: bool = False                   # ask Gemini to generate SQL


class QueryResultTable(BaseModel):
    table_id: uuid.UUID
    table_name: str
    display_name: Optional[str] = None
    section: str
    relevance_score: float
    matched_columns: list[str] = []
    match_reason: Optional[str] = None


class QueryResponse(BaseModel):
    query_id: uuid.UUID
    question: str
    section_filter: Optional[str] = None
    primary_results: list[QueryResultTable] = []
    cross_section_expansions: list[QueryResultTable] = []
    suggested_sql: Optional[str] = None
    explanation: Optional[str] = None


class QueryHistoryResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    question: str
    section_filter: Optional[str] = None
    result_tables: Optional[dict[str, Any]] = None
    generated_sql: Optional[str] = None
    feedback: FeedbackType
    created_at: datetime

    model_config = {"from_attributes": True}


class QueryHistoryListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[QueryHistoryResponse]


class FeedbackRequest(BaseModel):
    feedback: FeedbackType
