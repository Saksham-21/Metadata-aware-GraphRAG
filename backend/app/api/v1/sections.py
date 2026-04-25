"""
app/api/v1/sections.py
──────────────────────
Section CRUD routes:
  GET    /sections        → All — list active sections
  POST   /sections        → Admin — create section
  GET    /sections/{id}   → All — get single section
  PATCH  /sections/{id}   → Admin — update section
  DELETE /sections/{id}   → Admin — soft-delete section
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, require_admin
from app.models.history import ActionType, EditHistory, EntityType
from app.models.section import Section
from app.models.user import User
from app.schemas.section import (
    CreateSectionRequest,
    SectionListResponse,
    SectionResponse,
    UpdateSectionRequest,
)

router = APIRouter(prefix="/sections", tags=["Sections"])


def _snapshot(section: Section) -> dict:
    """Serialize section to a plain dict for history snapshots."""
    return {
        "id": str(section.id),
        "name": section.name,
        "display_name": section.display_name,
        "description": section.description,
        "is_active": section.is_active,
    }


# ── List ──────────────────────────────────────────────────────────────────────
@router.get("", response_model=SectionListResponse)
async def list_sections(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
    include_inactive: bool = False,
):
    query = select(Section)
    if not include_inactive:
        query = query.where(Section.is_active == True)
    query = query.order_by(Section.display_name)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()
    items = (await db.execute(query)).scalars().all()
    return SectionListResponse(total=total, items=list(items))


# ── Create ────────────────────────────────────────────────────────────────────
@router.post("", response_model=SectionResponse, status_code=status.HTTP_201_CREATED)
async def create_section(
    body: CreateSectionRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    existing = (await db.execute(select(Section).where(Section.name == body.name))).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Section '{body.name}' already exists.",
        )

    section = Section(
        name=body.name,
        display_name=body.display_name,
        description=body.description,
        created_by=admin.id,
    )
    db.add(section)
    await db.flush()

    # Record history
    db.add(EditHistory(
        entity_type=EntityType.SECTION,
        entity_id=section.id,
        entity_name=section.name,
        action=ActionType.CREATE,
        changed_by=admin.id,
        after_state=_snapshot(section),
        change_summary=f"Created section '{section.display_name}'",
    ))
    return section


# ── Get Single ────────────────────────────────────────────────────────────────
@router.get("/{section_id}", response_model=SectionResponse)
async def get_section(
    section_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    section = (await db.execute(select(Section).where(Section.id == section_id))).scalar_one_or_none()
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found.")
    return section


# ── Update ────────────────────────────────────────────────────────────────────
@router.patch("/{section_id}", response_model=SectionResponse)
async def update_section(
    section_id: uuid.UUID,
    body: UpdateSectionRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    section = (await db.execute(select(Section).where(Section.id == section_id))).scalar_one_or_none()
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found.")

    before = _snapshot(section)
    changes = []

    if body.display_name is not None:
        section.display_name = body.display_name
        changes.append("display_name")
    if body.description is not None:
        section.description = body.description
        changes.append("description")
    if body.is_active is not None:
        section.is_active = body.is_active
        changes.append("is_active")

    await db.flush()

    db.add(EditHistory(
        entity_type=EntityType.SECTION,
        entity_id=section.id,
        entity_name=section.name,
        action=ActionType.UPDATE,
        changed_by=admin.id,
        before_state=before,
        after_state=_snapshot(section),
        change_summary=f"Updated {', '.join(changes)} on section '{section.name}'",
    ))
    return section


# ── Soft Delete ───────────────────────────────────────────────────────────────
@router.delete("/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_section(
    section_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    section = (await db.execute(select(Section).where(Section.id == section_id))).scalar_one_or_none()
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found.")

    before = _snapshot(section)
    section.is_active = False
    await db.flush()

    db.add(EditHistory(
        entity_type=EntityType.SECTION,
        entity_id=section.id,
        entity_name=section.name,
        action=ActionType.DELETE,
        changed_by=admin.id,
        before_state=before,
        after_state=_snapshot(section),
        change_summary=f"Soft-deleted section '{section.name}'",
    ))
    return None
