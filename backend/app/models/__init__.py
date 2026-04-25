"""
app/models/__init__.py
──────────────────────
Import all models here so that:
  1. Alembic's env.py can find all metadata via a single import.
  2. SQLAlchemy's relationship() backrefs resolve without circular imports.
"""

from app.models.user import User, UserRole                          # noqa: F401
from app.models.section import Section                              # noqa: F401
from app.models.table_meta import TableMeta, TableSection           # noqa: F401
from app.models.column import Column                                # noqa: F401
from app.models.history import EditHistory, QueryHistory            # noqa: F401
from app.models.history import EntityType, ActionType, FeedbackType # noqa: F401
