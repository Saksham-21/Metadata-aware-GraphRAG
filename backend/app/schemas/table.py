"""
app/schemas/table.py
────────────────────
Pydantic schemas for TableMeta — create, update, and response shapes.
Columns are nested inside the full table response.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.column import ColumnResponse, CreateColumnRequest
from app.schemas.section import SectionResponse


# ── Create ──────────────────────────────────────────────────────────────────
class CreateTableRequest(BaseModel):
    table_name: str = Field(
        ..., min_length=1, max_length=255,
        description="Must be globally unique across the organisation."
    )
    display_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    primary_section_id: Optional[uuid.UUID] = None
    tags: Optional[list[str]] = None
    # Columns can be submitted together with the table in one request
    columns: Optional[list[CreateColumnRequest]] = None
    # Secondary section IDs (in addition to primary)
    secondary_section_ids: Optional[list[uuid.UUID]] = None


# ── Update ──────────────────────────────────────────────────────────────────
class UpdateTableRequest(BaseModel):
    """
    Developer: can update any field below.
    BA: only description and tags are permitted — enforced in the route handler.
    """
    display_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    primary_section_id: Optional[uuid.UUID] = None
    tags: Optional[list[str]] = None
    is_active: Optional[bool] = None


# ── Responses ────────────────────────────────────────────────────────────────
class TableSummaryResponse(BaseModel):
    """Lightweight response for list views — no columns included."""
    id: uuid.UUID
    table_name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    primary_section_id: Optional[uuid.UUID] = None
    primary_section_name: Optional[str] = None   # denormalised for convenience
    tags: Optional[list[str]] = None
    is_active: bool
    created_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TableResponse(TableSummaryResponse):
    """Full detail response — includes all columns and section memberships."""
    columns: list[ColumnResponse] = []
    secondary_sections: list[SectionResponse] = []

    model_config = {"from_attributes": True}


class TableListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[TableSummaryResponse]


# ── Section membership ────────────────────────────────────────────────────────
class AddTableSectionRequest(BaseModel):
    section_id: uuid.UUID
