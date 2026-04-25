"""
app/services/ingestion.py
──────────────────────────
Ingestion Service — keeps PostgreSQL, ChromaDB, and Neo4j in sync.

Phase 1  (current): PostgreSQL only. All ChromaDB/Neo4j calls are stubbed.
Phase 2  (next):    Uncomment the ChromaDB and Neo4j blocks below and wire in
                    the real clients from app/db/chromadb.py and app/db/neo4j.py.

Called from:
  - tables.py on every create/update/delete of a table or column
  - admin.py on force reindex
"""

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.column import Column
from app.models.section import Section
from app.models.table_meta import TableMeta


class IngestionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        # Phase 2: self.chroma = get_chroma_client()
        # Phase 2: self.neo4j = get_neo4j_driver()

    # ── Public API ────────────────────────────────────────────────────────────

    async def sync_table(self, table_id: uuid.UUID) -> None:
        """
        Full sync of a single table (all its columns, sections, FK links)
        into ChromaDB and Neo4j.

        Called after any create or update on a table or its columns.
        """
        table = await self._load_table(table_id)
        if not table:
            return
        await self._upsert_chroma(table)
        await self._upsert_neo4j(table)

    async def remove_table(self, table_id: uuid.UUID) -> None:
        """
        Mark a table as inactive in ChromaDB and Neo4j.
        Does NOT hard-delete from the graph — preserves relationship history.
        """
        await self._deactivate_chroma(table_id)
        await self._deactivate_neo4j(table_id)

    async def full_reindex(self) -> dict:
        """
        Re-sync ALL active tables from PostgreSQL → ChromaDB + Neo4j.
        Called from /admin/reindex. Idempotent — safe to call multiple times.
        """
        result = await self.db.execute(
            select(TableMeta)
            .where(TableMeta.is_active == True)
            .options(selectinload(TableMeta.columns), selectinload(TableMeta.table_sections))
        )
        tables = result.scalars().all()

        synced = 0
        errors = []
        for table in tables:
            try:
                await self._upsert_chroma(table)
                await self._upsert_neo4j(table)
                synced += 1
            except Exception as e:
                errors.append({"table": table.table_name, "error": str(e)})

        return {"synced": synced, "errors": errors}

    # ── ChromaDB ──────────────────────────────────────────────────────────────

    async def _upsert_chroma(self, table: TableMeta) -> None:
        """
        Embed and upsert a table's metadata into the ChromaDB collection.

        Document structure per table:
          id       = table UUID string
          document = "table_name: {name}\ndescription: {desc}\ncolumns: {col list}"
          metadata = { section, tags, column_names, column_types, business_terms }

        Phase 2 implementation:
        ---
        collection = self.chroma.get_or_create_collection(
            name=f"{settings.CHROMA_COLLECTION_PREFIX}_tables",
            metadata={"hnsw:space": "cosine"},
        )
        doc_text = self._build_document_text(table)
        metadata = self._build_metadata(table)
        collection.upsert(
            ids=[str(table.id)],
            documents=[doc_text],
            metadatas=[metadata],
        )
        """
        # STUB — Phase 1
        pass

    async def _deactivate_chroma(self, table_id: uuid.UUID) -> None:
        """
        Remove a table's embedding from ChromaDB.

        Phase 2:
        ---
        collection = self.chroma.get_collection(...)
        collection.delete(ids=[str(table_id)])
        """
        # STUB — Phase 1
        pass

    # ── Neo4j ─────────────────────────────────────────────────────────────────

    async def _upsert_neo4j(self, table: TableMeta) -> None:
        """
        Upsert a table node and its relationships in Neo4j.

        Cypher (Phase 2):
        ---
        MERGE (t:Table {id: $id})
        SET t.name = $name, t.description = $description,
            t.section = $section, t.is_active = true

        // Columns
        FOREACH (col IN $columns |
            MERGE (c:Column {id: col.id})
            SET c.name = col.name, c.type = col.type
            MERGE (t)-[:HAS_COLUMN]->(c)
        )

        // Section membership
        MERGE (s:Section {name: $section_name})
        MERGE (t)-[:BELONGS_TO]->(s)

        // FK edges
        FOREACH (fk IN $fk_refs |
            MATCH (target:Table {id: fk.target_table_id})
            MERGE (t)-[:REFERENCES {column: fk.column_name}]->(target)
        )
        """
        # STUB — Phase 1
        pass

    async def _deactivate_neo4j(self, table_id: uuid.UUID) -> None:
        """
        Mark table node inactive in Neo4j (do NOT delete — preserve edges).

        Phase 2:
        ---
        MATCH (t:Table {id: $id})
        SET t.is_active = false
        """
        # STUB — Phase 1
        pass

    # ── Document builders (used by ChromaDB upsert) ───────────────────────────

    def _build_document_text(self, table: TableMeta) -> str:
        """Build the text that will be embedded for this table."""
        parts = [f"Table: {table.table_name}"]
        if table.display_name:
            parts.append(f"Display name: {table.display_name}")
        if table.description:
            parts.append(f"Description: {table.description}")
        if table.tags:
            parts.append(f"Tags: {', '.join(table.tags)}")

        active_cols = [c for c in table.columns if c.is_active]
        if active_cols:
            col_lines = []
            for c in active_cols:
                col_line = f"  - {c.column_name} ({c.data_type})"
                if c.description:
                    col_line += f": {c.description}"
                if c.business_term:
                    col_line += f" [business term: {c.business_term}]"
                col_lines.append(col_line)
            parts.append("Columns:\n" + "\n".join(col_lines))

        return "\n".join(parts)

    def _build_metadata(self, table: TableMeta) -> dict:
        """Build ChromaDB metadata dict (used for filtering)."""
        active_cols = [c for c in table.columns if c.is_active]
        return {
            "table_id": str(table.id),
            "table_name": table.table_name,
            "section_id": str(table.primary_section_id) if table.primary_section_id else "",
            "tags": ",".join(table.tags or []),
            "column_names": ",".join(c.column_name for c in active_cols),
            "business_terms": ",".join(c.business_term for c in active_cols if c.business_term),
        }

    async def _load_table(self, table_id: uuid.UUID) -> Optional[TableMeta]:
        result = await self.db.execute(
            select(TableMeta)
            .where(TableMeta.id == table_id)
            .options(selectinload(TableMeta.columns), selectinload(TableMeta.table_sections))
        )
        return result.scalar_one_or_none()
