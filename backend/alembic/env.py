"""
alembic/env.py
──────────────
Alembic migration environment.

Uses psycopg2 (synchronous) for running migrations.
The async asyncpg driver used at runtime cannot be used by Alembic,
so we use SYNC_DATABASE_URL (postgresql+psycopg2://...) here.

To generate a new migration after changing models:
    alembic revision --autogenerate -m "describe your change"

To apply migrations:
    alembic upgrade head

To rollback one step:
    alembic downgrade -1
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ── Ensure the project root is on sys.path so 'app' is importable ────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Load environment variables from .env ─────────────────────────────────────
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# ── Import app settings and ALL models (so Alembic sees the metadata) ─────────
from app.core.config import settings
import app.models  # noqa: F401  — registers all models with Base.metadata
from app.db.postgres import Base

# ── Alembic Config object ─────────────────────────────────────────────────────
config = context.config

# Set the SQLAlchemy URL dynamically from settings
# Uses SYNC_DATABASE_URL (psycopg2) — NOT asyncpg
config.set_main_option("sqlalchemy.url", settings.SYNC_DATABASE_URL)

# Interpret the config file for logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata for autogenerate support
target_metadata = Base.metadata


# ── Run migrations ────────────────────────────────────────────────────────────
def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode — generates SQL script without a DB connection.
    Useful for reviewing what will be applied before running it.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,          # detect column type changes
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode — connects to the DB and applies changes.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,    # don't pool connections during migrations
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
