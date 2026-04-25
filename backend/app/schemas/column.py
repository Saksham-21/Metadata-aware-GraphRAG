"""
app/schemas/column.py
─────────────────────
Pydantic schemas for Column — used both standalone and nested inside TableResponse.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Create ──────────────────────────────────────────────────────────────────
class CreateColumnRequest(BaseModel):
    column_name: str = Field(..., min_length=1, max_length=255)
    data_type: str = Field(..., min_length=1, max_length=100, description="e.g. VARCHAR, DECIMAL, TIMESTAMP")
    description: Optional[str] = None
    is_nullable: bool = True
    is_primary_key: bool = False
    is_foreign_key: bool = False
    fk_references_table_id: Optional[uuid.UUID] = None
    fk_references_column: Optional[str] = Field(None, max_length=255)
    business_term: Optional[str] = Field(None, max_length=255)
    sample_values: Optional[list[str]] = None


# ── Update ──────────────────────────────────────────────────────────────────
class UpdateColumnRequest(BaseModel):
    """
    Developer: can update any field.
    BA: can only update description, business_term, sample_values.
    Role enforcement happens in the route handler.
    """
    column_name: Optional[str] = Field(None, min_length=1, max_length=255)
    data_type: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    is_nullable: Optional[bool] = None
    is_primary_key: Optional[bool] = None
    is_foreign_key: Optional[bool] = None
    fk_references_table_id: Optional[uuid.UUID] = None
    fk_references_column: Optional[str] = Field(None, max_length=255)
    business_term: Optional[str] = Field(None, max_length=255)
    sample_values: Optional[list[str]] = None


# ── Responses ────────────────────────────────────────────────────────────────
class ColumnResponse(BaseModel):
    id: uuid.UUID
    table_id: uuid.UUID
    column_name: str
    data_type: str
    description: Optional[str] = None
    is_nullable: bool
    is_primary_key: bool
    is_foreign_key: bool
    fk_references_table_id: Optional[uuid.UUID] = None
    fk_references_column: Optional[str] = None
    business_term: Optional[str] = None
    sample_values: Optional[list[str]] = None
    is_active: bool
    created_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
