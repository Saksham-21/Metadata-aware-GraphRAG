"""
app/models/section.py
─────────────────────
Section — a business domain category for tables.

Examples: credit_card, customer_loan, deposits, customer_profile, risk_management

Every table has ONE primary section. It can also belong to additional
secondary sections via the table_sections association table.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres import Base


class Section(Base):
    __tablename__ = "sections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # URL-safe slug, globally unique. e.g. "credit_card"
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    # Human-readable label. e.g. "Credit Card"
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # ── Relationships ──────────────────────────────────────────
    # Tables whose primary section is this one
    primary_tables = relationship(
        "TableMeta", back_populates="primary_section", foreign_keys="TableMeta.primary_section_id"
    )
    # All table–section memberships (including secondary)
    table_sections = relationship("TableSection", back_populates="section")

    def __repr__(self) -> str:
        return f"<Section name={self.name}>"
