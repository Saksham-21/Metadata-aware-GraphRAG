"""
app/models/column.py
────────────────────
Column — a column inside a TableMeta entry.

Each column tracks:
  - Name, data type, nullability, PK/FK flags
  - FK reference (which table + column it points to)
  - Business glossary term (human-readable name used by BAs)
  - Sample values for context during query-time LLM reasoning
  - Description (editable by both Developers and BAs)
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


class Column(Base):
    __tablename__ = "columns"
    __table_args__ = (
        # A column name must be unique within a table
        UniqueConstraint("table_id", "column_name", name="uq_table_column"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    table_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tables.id", ondelete="CASCADE"), nullable=False, index=True
    )
    column_name: Mapped[str] = mapped_column(String(255), nullable=False)
    data_type: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "VARCHAR", "DECIMAL"
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Structural flags
    is_nullable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_primary_key: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_foreign_key: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # FK target — only populated when is_foreign_key = True
    fk_references_table_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tables.id", ondelete="SET NULL"), nullable=True
    )
    fk_references_column: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Business glossary term — e.g. "Transaction Amount" for column txn_amt
    business_term: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # A few sample values to help LLM understand content e.g. ["2024-01-01", "2024-06-15"]
    sample_values: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True, default=list
    )

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
    # Use string-based foreign_keys to avoid column object reference issues at class definition time
    table = relationship(
        "TableMeta",
        back_populates="columns",
        foreign_keys="[Column.table_id]",
    )
    # The table this column FK-references (nullable — only set when is_foreign_key=True)
    fk_target_table = relationship(
        "TableMeta",
        foreign_keys="[Column.fk_references_table_id]",
    )

    def __repr__(self) -> str:
        return f"<Column table={self.table_id} name={self.column_name}>"
