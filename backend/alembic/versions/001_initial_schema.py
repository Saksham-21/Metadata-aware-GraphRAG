"""Initial schema — all tables

Revision ID: 001
Revises:
Create Date: 2026-04-15

Creates:
  - user_role_enum
  - entity_type_enum
  - action_type_enum
  - feedback_type_enum
  - users
  - sections
  - tables
  - table_sections
  - columns
  - edit_history
  - query_history
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enum types ────────────────────────────────────────────────────────────
    user_role_enum = postgresql.ENUM(
        "admin", "developer", "ba", "viewer",
        name="user_role_enum", create_type=False
    )
    entity_type_enum = postgresql.ENUM(
        "table", "column", "section",
        name="entity_type_enum", create_type=False
    )
    action_type_enum = postgresql.ENUM(
        "create", "update", "delete",
        name="action_type_enum", create_type=False
    )
    feedback_type_enum = postgresql.ENUM(
        "positive", "negative", "none",
        name="feedback_type_enum", create_type=False
    )

    user_role_enum.create(op.get_bind(), checkfirst=True)
    entity_type_enum.create(op.get_bind(), checkfirst=True)
    action_type_enum.create(op.get_bind(), checkfirst=True)
    feedback_type_enum.create(op.get_bind(), checkfirst=True)

    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM("admin", "developer", "ba", "viewer", name="user_role_enum", create_type=False),
            nullable=False,
            server_default="viewer",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── sections ──────────────────────────────────────────────────────────────
    op.create_table(
        "sections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_sections_name"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_sections_name", "sections", ["name"], unique=True)

    # ── tables ────────────────────────────────────────────────────────────────
    op.create_table(
        "tables",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("table_name", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("primary_section_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("table_name", name="uq_tables_table_name"),
        sa.ForeignKeyConstraint(["primary_section_id"], ["sections.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_tables_table_name", "tables", ["table_name"], unique=True)

    # ── table_sections ────────────────────────────────────────────────────────
    op.create_table(
        "table_sections",
        sa.Column("table_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("section_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("table_id", "section_id"),
        sa.UniqueConstraint("table_id", "section_id", name="uq_table_section"),
        sa.ForeignKeyConstraint(["table_id"], ["tables.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["section_id"], ["sections.id"], ondelete="CASCADE"),
    )

    # ── columns ───────────────────────────────────────────────────────────────
    op.create_table(
        "columns",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("table_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("column_name", sa.String(255), nullable=False),
        sa.Column("data_type", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_nullable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_primary_key", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_foreign_key", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("fk_references_table_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("fk_references_column", sa.String(255), nullable=True),
        sa.Column("business_term", sa.String(255), nullable=True),
        sa.Column("sample_values", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("table_id", "column_name", name="uq_table_column"),
        sa.ForeignKeyConstraint(["table_id"], ["tables.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["fk_references_table_id"], ["tables.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_columns_table_id", "columns", ["table_id"])

    # ── edit_history ──────────────────────────────────────────────────────────
    op.create_table(
        "edit_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column(
            "entity_type",
            postgresql.ENUM("table", "column", "section", name="entity_type_enum", create_type=False),
            nullable=False,
        ),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_name", sa.String(255), nullable=True),
        sa.Column(
            "action",
            postgresql.ENUM("create", "update", "delete", name="action_type_enum", create_type=False),
            nullable=False,
        ),
        sa.Column("changed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("before_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["changed_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_edit_history_entity_type", "edit_history", ["entity_type"])
    op.create_index("ix_edit_history_entity_id", "edit_history", ["entity_id"])
    op.create_index("ix_edit_history_changed_at", "edit_history", ["changed_at"])

    # ── query_history ─────────────────────────────────────────────────────────
    op.create_table(
        "query_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("section_filter", sa.String(100), nullable=True),
        sa.Column("result_tables", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("generated_sql", sa.Text(), nullable=True),
        sa.Column(
            "feedback",
            postgresql.ENUM("positive", "negative", "none", name="feedback_type_enum", create_type=False),
            nullable=False,
            server_default="none",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_query_history_user_id", "query_history", ["user_id"])
    op.create_index("ix_query_history_created_at", "query_history", ["created_at"])


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_table("query_history")
    op.drop_table("edit_history")
    op.drop_table("columns")
    op.drop_table("table_sections")
    op.drop_table("tables")
    op.drop_table("sections")
    op.drop_table("users")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS feedback_type_enum")
    op.execute("DROP TYPE IF EXISTS action_type_enum")
    op.execute("DROP TYPE IF EXISTS entity_type_enum")
    op.execute("DROP TYPE IF EXISTS user_role_enum")
