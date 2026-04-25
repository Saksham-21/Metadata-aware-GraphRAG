"""
app/api/v1/tables.py
────────────────────
Table CRUD + column management + section membership:

  POST   /tables                              → Developer — create table (+columns)
  GET    /tables                              → All — list (paginated, section filter)
  GET    /tables/{id}                         → All — full detail with columns
  PATCH  /tables/{id}                         → Developer/BA — update metadata
  DELETE /tables/{id}                         → Developer — soft delete

  POST   /tables/{id}/columns                 → Developer — add column
  PATCH  /tables/{id}/columns/{col_id}        → Developer/BA — update column
  DELETE /tables/{id}/columns/{col_id}        → Developer — remove column

  POST   /tables/{id}/sections                → Developer — add secondary section
  DELETE /tables/{id}/sections/{section_id}   → Developer — remove secondary section

History is recorded on every write.
ChromaDB + Neo4j sync is called via the ingestion service (stub for now).
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import (
    get_current_user,
    get_db,
    require_ba_or_above,
    require_developer,
)
from app.core.security import Role
from app.models.column import Column
from app.models.history import ActionType, EditHistory, EntityType
from app.models.section import Section
from app.models.table_meta import TableMeta, TableSection
from app.models.user import User
from app.schemas.column import ColumnResponse, CreateColumnRequest, UpdateColumnRequest
from app.schemas.table import (
    AddTableSectionRequest,
    CreateTableRequest,
    TableListResponse,
    TableResponse,
    TableSummaryResponse,
    UpdateTableRequest,
)

router = APIRouter(prefix="/tables", tags=["Tables"])


# ── Helpers ───────────────────────────────────────────────────────────────────
def _table_snapshot(table: TableMeta) -> dict:
    return {
        "id": str(table.id),
        "table_name": table.table_name,
        "display_name": table.display_name,
        "description": table.description,
        "primary_section_id": str(table.primary_section_id) if table.primary_section_id else None,
        "tags": table.tags,
        "is_active": table.is_active,
    }


def _column_snapshot(col: Column) -> dict:
    return {
        "id": str(col.id),
        "column_name": col.column_name,
        "data_type": col.data_type,
        "description": col.description,
        "is_nullable": col.is_nullable,
        "is_primary_key": col.is_primary_key,
        "is_foreign_key": col.is_foreign_key,
        "fk_references_table_id": str(col.fk_references_table_id) if col.fk_references_table_id else None,
        "fk_references_column": col.fk_references_column,
        "business_term": col.business_term,
        "sample_values": col.sample_values,
        "is_active": col.is_active,
    }


async def _get_table_or_404(db: AsyncSession, table_id: uuid.UUID) -> TableMeta:
    result = await db.execute(
        select(TableMeta)
        .where(TableMeta.id == table_id)
        .options(selectinload(TableMeta.columns), selectinload(TableMeta.table_sections))
    )
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found.")
    return table


# ── Create Table ──────────────────────────────────────────────────────────────
@router.post("", response_model=TableResponse, status_code=status.HTTP_201_CREATED)
async def create_table(
    body: CreateTableRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_developer),
):
    # Uniqueness check
    existing = (await db.execute(
        select(TableMeta).where(TableMeta.table_name == body.table_name)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Table '{body.table_name}' already exists in the Knowledge Base.",
        )

    table = TableMeta(
        table_name=body.table_name,
        display_name=body.display_name,
        description=body.description,
        primary_section_id=body.primary_section_id,
        tags=body.tags or [],
        created_by=current_user.id,
    )
    db.add(table)
    await db.flush()  # get table.id

    # Add columns if provided
    for col_data in (body.columns or []):
        col = Column(
            table_id=table.id,
            column_name=col_data.column_name,
            data_type=col_data.data_type,
            description=col_data.description,
            is_nullable=col_data.is_nullable,
            is_primary_key=col_data.is_primary_key,
            is_foreign_key=col_data.is_foreign_key,
            fk_references_table_id=col_data.fk_references_table_id,
            fk_references_column=col_data.fk_references_column,
            business_term=col_data.business_term,
            sample_values=col_data.sample_values or [],
            created_by=current_user.id,
        )
        db.add(col)

    # Add secondary sections
    for sec_id in (body.secondary_section_ids or []):
        db.add(TableSection(table_id=table.id, section_id=sec_id))

    await db.flush()

    # History
    db.add(EditHistory(
        entity_type=EntityType.TABLE,
        entity_id=table.id,
        entity_name=table.table_name,
        action=ActionType.CREATE,
        changed_by=current_user.id,
        after_state=_table_snapshot(table),
        change_summary=f"Created table '{table.table_name}' with {len(body.columns or [])} column(s).",
    ))

    # TODO: trigger ingestion service → ChromaDB + Neo4j sync
    # await ingestion_service.sync_table(db, table)

    # Reload with full relationships for the response
    return await _get_table_or_404(db, table.id)


# ── List Tables ───────────────────────────────────────────────────────────────
@router.get("", response_model=TableListResponse)
async def list_tables(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
    section_id: uuid.UUID | None = Query(None, description="Filter by primary section"),
    section_name: str | None = Query(None, description="Filter by section slug"),
    search: str | None = Query(None, description="Substring match on table_name or description"),
    include_inactive: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = select(TableMeta)

    if not include_inactive:
        query = query.where(TableMeta.is_active == True)
    if section_id:
        query = query.where(TableMeta.primary_section_id == section_id)
    if section_name:
        sec = (await db.execute(
            select(Section).where(Section.name == section_name)
        )).scalar_one_or_none()
        if sec:
            query = query.where(TableMeta.primary_section_id == sec.id)
    if search:
        pattern = f"%{search}%"
        query = query.where(
            TableMeta.table_name.ilike(pattern) | TableMeta.description.ilike(pattern)
        )

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    offset = (page - 1) * page_size
    items = (await db.execute(
        query.order_by(TableMeta.table_name).offset(offset).limit(page_size)
    )).scalars().all()

    # Denormalise section name for each item
    section_cache: dict[uuid.UUID, str] = {}
    response_items = []
    for t in items:
        sec_name = None
        if t.primary_section_id:
            if t.primary_section_id not in section_cache:
                sec = (await db.execute(
                    select(Section).where(Section.id == t.primary_section_id)
                )).scalar_one_or_none()
                section_cache[t.primary_section_id] = sec.name if sec else ""
            sec_name = section_cache[t.primary_section_id]
        d = TableSummaryResponse.model_validate(t)
        d.primary_section_name = sec_name
        response_items.append(d)

    return TableListResponse(total=total, page=page, page_size=page_size, items=response_items)


# ── Get Single Table ──────────────────────────────────────────────────────────
@router.get("/{table_id}", response_model=TableResponse)
async def get_table(
    table_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    table = await _get_table_or_404(db, table_id)
    active_cols = [c for c in table.columns if c.is_active]

    # Build secondary sections list
    sec_ids = [ts.section_id for ts in table.table_sections]
    secondary_sections = []
    for sid in sec_ids:
        sec = (await db.execute(select(Section).where(Section.id == sid))).scalar_one_or_none()
        if sec:
            secondary_sections.append(sec)

    resp = TableResponse.model_validate(table)
    resp.columns = [ColumnResponse.model_validate(c) for c in active_cols]
    resp.secondary_sections = secondary_sections
    return resp


# ── Update Table ──────────────────────────────────────────────────────────────
@router.patch("/{table_id}", response_model=TableResponse)
async def update_table(
    table_id: uuid.UUID,
    body: UpdateTableRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_ba_or_above),
):
    table = await _get_table_or_404(db, table_id)
    before = _table_snapshot(table)
    changes = []

    # BAs can only update description and tags
    if current_user.role == Role.BA:
        allowed = {"description", "tags"}
        requested = {k for k, v in body.model_dump(exclude_none=True).items()}
        disallowed = requested - allowed
        if disallowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"BAs can only update: description, tags. Disallowed fields: {disallowed}",
            )

    if body.display_name is not None:
        table.display_name = body.display_name; changes.append("display_name")
    if body.description is not None:
        table.description = body.description; changes.append("description")
    if body.primary_section_id is not None:
        table.primary_section_id = body.primary_section_id; changes.append("primary_section_id")
    if body.tags is not None:
        table.tags = body.tags; changes.append("tags")
    if body.is_active is not None:
        table.is_active = body.is_active; changes.append("is_active")

    table.updated_at = datetime.now(timezone.utc)
    await db.flush()

    db.add(EditHistory(
        entity_type=EntityType.TABLE,
        entity_id=table.id,
        entity_name=table.table_name,
        action=ActionType.UPDATE,
        changed_by=current_user.id,
        before_state=before,
        after_state=_table_snapshot(table),
        change_summary=f"Updated {', '.join(changes)} on table '{table.table_name}'",
    ))

    # TODO: await ingestion_service.sync_table(db, table)
    return await _get_table_or_404(db, table_id)


# ── Soft Delete Table ─────────────────────────────────────────────────────────
@router.delete("/{table_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_table(
    table_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_developer),
):
    table = await _get_table_or_404(db, table_id)
    before = _table_snapshot(table)
    table.is_active = False
    table.updated_at = datetime.now(timezone.utc)
    await db.flush()

    db.add(EditHistory(
        entity_type=EntityType.TABLE,
        entity_id=table.id,
        entity_name=table.table_name,
        action=ActionType.DELETE,
        changed_by=current_user.id,
        before_state=before,
        after_state=_table_snapshot(table),
        change_summary=f"Soft-deleted table '{table.table_name}'",
    ))
    # TODO: await ingestion_service.remove_table(table.id)
    return None


# ── Add Column ────────────────────────────────────────────────────────────────
@router.post("/{table_id}/columns", response_model=ColumnResponse, status_code=status.HTTP_201_CREATED)
async def add_column(
    table_id: uuid.UUID,
    body: CreateColumnRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_developer),
):
    table = await _get_table_or_404(db, table_id)

    # Uniqueness within table
    dup = (await db.execute(
        select(Column).where(
            Column.table_id == table_id,
            Column.column_name == body.column_name,
            Column.is_active == True,
        )
    )).scalar_one_or_none()
    if dup:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Column '{body.column_name}' already exists in table '{table.table_name}'.",
        )

    col = Column(
        table_id=table_id,
        column_name=body.column_name,
        data_type=body.data_type,
        description=body.description,
        is_nullable=body.is_nullable,
        is_primary_key=body.is_primary_key,
        is_foreign_key=body.is_foreign_key,
        fk_references_table_id=body.fk_references_table_id,
        fk_references_column=body.fk_references_column,
        business_term=body.business_term,
        sample_values=body.sample_values or [],
        created_by=current_user.id,
    )
    db.add(col)
    await db.flush()

    db.add(EditHistory(
        entity_type=EntityType.COLUMN,
        entity_id=col.id,
        entity_name=f"{table.table_name}.{col.column_name}",
        action=ActionType.CREATE,
        changed_by=current_user.id,
        after_state=_column_snapshot(col),
        change_summary=f"Added column '{col.column_name}' to table '{table.table_name}'",
    ))
    # TODO: await ingestion_service.sync_table(db, table)
    return col


# ── Update Column ─────────────────────────────────────────────────────────────
@router.patch("/{table_id}/columns/{column_id}", response_model=ColumnResponse)
async def update_column(
    table_id: uuid.UUID,
    column_id: uuid.UUID,
    body: UpdateColumnRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_ba_or_above),
):
    table = await _get_table_or_404(db, table_id)
    result = await db.execute(
        select(Column).where(Column.id == column_id, Column.table_id == table_id)
    )
    col = result.scalar_one_or_none()
    if not col:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Column not found.")

    before = _column_snapshot(col)
    changes = []

    # BAs can only update description, business_term, sample_values
    if current_user.role == Role.BA:
        requested = {k for k, v in body.model_dump(exclude_none=True).items()}
        ba_allowed = {"description", "business_term", "sample_values"}
        disallowed = requested - ba_allowed
        if disallowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"BAs can only update: {ba_allowed}. Disallowed: {disallowed}",
            )

    if body.column_name is not None:
        col.column_name = body.column_name; changes.append("column_name")
    if body.data_type is not None:
        col.data_type = body.data_type; changes.append("data_type")
    if body.description is not None:
        col.description = body.description; changes.append("description")
    if body.is_nullable is not None:
        col.is_nullable = body.is_nullable; changes.append("is_nullable")
    if body.is_primary_key is not None:
        col.is_primary_key = body.is_primary_key; changes.append("is_primary_key")
    if body.is_foreign_key is not None:
        col.is_foreign_key = body.is_foreign_key; changes.append("is_foreign_key")
    if body.fk_references_table_id is not None:
        col.fk_references_table_id = body.fk_references_table_id
    if body.fk_references_column is not None:
        col.fk_references_column = body.fk_references_column
    if body.business_term is not None:
        col.business_term = body.business_term; changes.append("business_term")
    if body.sample_values is not None:
        col.sample_values = body.sample_values; changes.append("sample_values")

    col.updated_at = datetime.now(timezone.utc)
    await db.flush()

    db.add(EditHistory(
        entity_type=EntityType.COLUMN,
        entity_id=col.id,
        entity_name=f"{table.table_name}.{col.column_name}",
        action=ActionType.UPDATE,
        changed_by=current_user.id,
        before_state=before,
        after_state=_column_snapshot(col),
        change_summary=f"Updated {', '.join(changes)} on column '{col.column_name}' in '{table.table_name}'",
    ))
    # TODO: await ingestion_service.sync_table(db, table)
    return col


# ── Soft Delete Column ────────────────────────────────────────────────────────
@router.delete("/{table_id}/columns/{column_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_column(
    table_id: uuid.UUID,
    column_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_developer),
):
    await _get_table_or_404(db, table_id)
    result = await db.execute(
        select(Column).where(Column.id == column_id, Column.table_id == table_id)
    )
    col = result.scalar_one_or_none()
    if not col:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Column not found.")

    before = _column_snapshot(col)
    col.is_active = False
    col.updated_at = datetime.now(timezone.utc)
    await db.flush()

    table_name = (await db.get(TableMeta, table_id)).table_name
    db.add(EditHistory(
        entity_type=EntityType.COLUMN,
        entity_id=col.id,
        entity_name=f"{table_name}.{col.column_name}",
        action=ActionType.DELETE,
        changed_by=current_user.id,
        before_state=before,
        after_state=_column_snapshot(col),
        change_summary=f"Removed column '{col.column_name}' from table '{table_name}'",
    ))
    return None


# ── Add Secondary Section ─────────────────────────────────────────────────────
@router.post("/{table_id}/sections", status_code=status.HTTP_201_CREATED)
async def add_table_section(
    table_id: uuid.UUID,
    body: AddTableSectionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_developer),
):
    table = await _get_table_or_404(db, table_id)
    section = (await db.execute(
        select(Section).where(Section.id == body.section_id)
    )).scalar_one_or_none()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found.")

    existing = (await db.execute(
        select(TableSection).where(
            TableSection.table_id == table_id,
            TableSection.section_id == body.section_id,
        )
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Table is already in that section.")

    db.add(TableSection(table_id=table_id, section_id=body.section_id))
    await db.flush()
    return {"message": f"Table '{table.table_name}' added to section '{section.name}'."}


# ── Remove Secondary Section ──────────────────────────────────────────────────
@router.delete("/{table_id}/sections/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_table_section(
    table_id: uuid.UUID,
    section_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_developer),
):
    ts = (await db.execute(
        select(TableSection).where(
            TableSection.table_id == table_id,
            TableSection.section_id == section_id,
        )
    )).scalar_one_or_none()
    if not ts:
        raise HTTPException(status_code=404, detail="Section membership not found.")
    await db.delete(ts)
    return None
