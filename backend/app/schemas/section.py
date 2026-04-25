"""
app/schemas/section.py
──────────────────────
Pydantic schemas for Sections.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator
import re


# ── Create ─────────────────────────────────────────────────────────────────
class CreateSectionRequest(BaseModel):
    name: str = Field(
        ..., min_length=2, max_length=100,
        description="URL-safe slug, e.g. 'credit_card'. Lowercase letters, digits, underscores only."
    )
    display_name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None

    @field_validator("name")
    @classmethod
    def slug_format(cls, v: str) -> str:
        v = v.lower().strip()
        if not re.match(r"^[a-z0-9_]+$", v):
            raise ValueError("Section name must contain only lowercase letters, digits, and underscores.")
        return v


# ── Update ─────────────────────────────────────────────────────────────────
class UpdateSectionRequest(BaseModel):
    display_name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None


# ── Responses ──────────────────────────────────────────────────────────────
class SectionResponse(BaseModel):
    id: uuid.UUID
    name: str
    display_name: str
    description: Optional[str] = None
    is_active: bool
    created_by: Optional[uuid.UUID] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SectionListResponse(BaseModel):
    total: int
    items: list[SectionResponse]
