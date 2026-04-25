"""
app/models/user.py
──────────────────
User ORM model.

Roles:
  admin      → Full access, only role that can register new users
  developer  → Can create/delete tables and columns, full ingestion
  ba         → Can only edit descriptions/business terms, cannot delete
  viewer     → Read-only access to tables and query (future use)
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    DEVELOPER = "developer"
    BA = "ba"
    VIEWER = "viewer"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role_enum", create_type=True,
             values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=UserRole.VIEWER,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    # Who registered this user (null for the first admin bootstrapped from env/CLI)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # ── Relationships ──────────────────────────────────────────
    # Back-references used in history/query lookups — lazy loaded
    edit_histories = relationship(
        "EditHistory", back_populates="changed_by_user", foreign_keys="EditHistory.changed_by"
    )
    query_histories = relationship(
        "QueryHistory", back_populates="user", foreign_keys="QueryHistory.user_id"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
