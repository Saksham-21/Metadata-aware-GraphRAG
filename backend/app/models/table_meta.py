"""
app/models/table_meta.py
────────────────────────
TableMeta — represents a database table in the Knowledge Base.

Named TableMeta (not Table) to avoid collision with SQLAlchemy's Table construct.

table_name is globally unique across the entire organisation.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres import Base


class TableMeta(Base):
    __tablename__ = "tables"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Globally unique across the org — mirrors actual DB table name
    table_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    # Friendly label for the UI
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Primary section (required)
    primary_section_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sections.id", ondelete="SET NULL"), nullable=True
    )
    # Free-form tags for extra searchability
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True, default=list)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ──────────────────────────────────────────
    primary_section = relationship(
        "Section", back_populates="primary_tables", foreign_keys=[primary_section_id]
    )
    # Secondary section memberships
    table_sections = relationship(
        "TableSection", back_populates="table", cascade="all, delete-orphan"
    )
    columns = relationship(
        "Column",
        back_populates="table",
        cascade="all, delete-orphan",
        foreign_keys="[Column.table_id]",   # disambiguate from Column.fk_references_table_id
    )

    def __repr__(self) -> str:
        return f"<TableMeta name={self.table_name}>"


class TableSection(Base):
    """
    Many-to-many association between tables and sections.
    A table can belong to multiple sections beyond its primary section.
    """
    __tablename__ = "table_sections"
    __table_args__ = (
        UniqueConstraint("table_id", "section_id", name="uq_table_section"),
    )

    table_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tables.id", ondelete="CASCADE"), primary_key=True
    )
    section_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sections.id", ondelete="CASCADE"), primary_key=True
    )

    # ── Relationships ──────────────────────────────────────────
    table = relationship("TableMeta", back_populates="table_sections")
    section = relationship("Section", back_populates="table_sections")

    def __repr__(self) -> str:
        return f"<TableSection table={self.table_id} section={self.section_id}>"
