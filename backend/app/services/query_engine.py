"""
app/services/query_engine.py
──────────────────────────────
Query Engine — the core AI pipeline.

Phase 1  (current): Stub only. Returns empty results.
Phase 2  (next):    Wire in ChromaDB + Neo4j + Gemini.

Pipeline steps:
  [1] Section filter  — resolve section_id or section_name to a section slug
  [2] ChromaDB search — semantic top-K retrieval (section-filtered)
  [3] Neo4j expansion — traverse FK graph to pull related tables
  [4] Merge + score   — combine semantic + graph scores
  [5] Gemini reasoning — final answer, column selection, optional SQL
  [6] Persist          — save to query_history
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.history import FeedbackType, QueryHistory
from app.models.section import Section
from app.models.user import User
from app.schemas.history import QueryRequest, QueryResponse, QueryResultTable


@dataclass
class RankedTable:
    table_id: uuid.UUID
    table_name: str
    display_name: Optional[str]
    section_name: str
    semantic_score: float
    graph_hop_distance: int = 0
    matched_columns: list[str] = field(default_factory=list)
    match_reason: Optional[str] = None
    is_cross_section: bool = False

    @property
    def combined_score(self) -> float:
        """
        Combined score formula: 60% semantic + 40% proximity.
        Graph hop distance of 0 = direct match (proximity = 1.0).
        """
        proximity = 1.0 / (1 + self.graph_hop_distance)
        return round(0.6 * self.semantic_score + 0.4 * proximity, 4)


class QueryEngine:
    def __init__(self, db: AsyncSession):
        self.db = db
        # Phase 2:
        # self.chroma = get_chroma_client()
        # self.neo4j = get_neo4j_driver()
        # self.gemini = GeminiClient()

    async def run(self, request: QueryRequest, user: User) -> QueryResponse:
        """Entry point called by the /query route."""

        # [1] Resolve section filter
        section_name = await self._resolve_section(request)

        # [2] ChromaDB semantic search
        chroma_results = await self._chroma_search(request.question, section_name)

        # [3] Neo4j graph expansion
        all_results = await self._graph_expand(chroma_results, section_name)

        # [4] Sort by combined score
        all_results.sort(key=lambda r: r.combined_score, reverse=True)

        # [5] Gemini reasoning
        explanation, sql = await self._gemini_reason(
            question=request.question,
            results=all_results[:20],
            include_sql=request.include_sql,
        )

        primary = [r for r in all_results if not r.is_cross_section]
        expansions = [r for r in all_results if r.is_cross_section]

        # [6] Persist to query history
        qh = QueryHistory(
            user_id=user.id,
            question=request.question,
            section_filter=section_name,
            result_tables={
                "primary_results": [self._to_dict(r) for r in primary],
                "cross_section_expansions": [self._to_dict(r) for r in expansions],
            },
            generated_sql=sql,
            feedback=FeedbackType.NONE,
        )
        self.db.add(qh)
        await self.db.flush()

        return QueryResponse(
            query_id=qh.id,
            question=request.question,
            section_filter=section_name,
            primary_results=[self._to_response(r) for r in primary],
            cross_section_expansions=[self._to_response(r) for r in expansions],
            suggested_sql=sql,
            explanation=explanation,
        )

    # ── Step 1 — Section Resolution ───────────────────────────────────────────

    async def _resolve_section(self, request: QueryRequest) -> Optional[str]:
        """Return the section slug if a section filter was requested."""
        if request.section_name:
            return request.section_name
        if request.section_id:
            sec = (await self.db.execute(
                select(Section).where(Section.id == request.section_id)
            )).scalar_one_or_none()
            return sec.name if sec else None
        return None   # no filter → search all sections

    # ── Step 2 — ChromaDB Semantic Search ────────────────────────────────────

    async def _chroma_search(
        self, question: str, section_name: Optional[str], top_k: int = 15
    ) -> list[RankedTable]:
        """
        Phase 2 implementation:
        ---
        where_filter = {"section": section_name} if section_name else None
        collection = self.chroma.get_collection(f"{settings.CHROMA_COLLECTION_PREFIX}_tables")
        results = collection.query(
            query_texts=[question],
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )
        ranked = []
        for i, table_id in enumerate(results["ids"][0]):
            meta = results["metadatas"][0][i]
            distance = results["distances"][0][i]
            semantic_score = 1 - distance   # cosine distance → similarity
            ranked.append(RankedTable(
                table_id=uuid.UUID(meta["table_id"]),
                table_name=meta["table_name"],
                display_name=None,
                section_name=meta.get("section_id", ""),
                semantic_score=semantic_score,
                matched_columns=meta.get("column_names", "").split(","),
            ))
        return ranked
        """
        # STUB — Phase 1
        return []

    # ── Step 3 — Neo4j Graph Expansion ───────────────────────────────────────

    async def _graph_expand(
        self, base_results: list[RankedTable], selected_section: Optional[str]
    ) -> list[RankedTable]:
        """
        For each table in base_results, traverse Neo4j [:REFERENCES] and
        [:RELATED_TO] edges up to 2 hops. Pull in linked tables even if they
        are in different sections (cross-section expansion).

        Phase 2 implementation:
        ---
        expanded = list(base_results)
        seen_ids = {r.table_id for r in base_results}
        async with self.neo4j.session() as neo_session:
            for r in base_results:
                cypher = '''
                    MATCH (t:Table {id: $id})-[:REFERENCES|RELATED_TO*1..2]-(related:Table)
                    WHERE related.is_active = true
                    RETURN related.id AS id,
                           related.name AS name,
                           related.section AS section,
                           min(length(path)) AS hop_distance
                '''
                result = await neo_session.run(cypher, id=str(r.table_id))
                async for record in result:
                    tid = uuid.UUID(record["id"])
                    if tid not in seen_ids:
                        seen_ids.add(tid)
                        expanded.append(RankedTable(
                            table_id=tid,
                            table_name=record["name"],
                            display_name=None,
                            section_name=record["section"],
                            semantic_score=r.semantic_score * 0.7,  # decay
                            graph_hop_distance=record["hop_distance"],
                            is_cross_section=(record["section"] != selected_section),
                            match_reason=f"Linked via graph from '{r.table_name}'",
                        ))
        return expanded
        """
        # STUB — Phase 1
        return base_results

    # ── Step 4 is inline (sort by combined_score in run()) ───────────────────

    # ── Step 5 — Gemini Reasoning ─────────────────────────────────────────────

    async def _gemini_reason(
        self,
        question: str,
        results: list[RankedTable],
        include_sql: bool,
    ) -> tuple[str, Optional[str]]:
        """
        Phase 2 implementation:
        ---
        context = self._build_gemini_context(results)
        prompt = f'''
        You are a data catalogue assistant.
        User question: {question}

        Relevant tables and columns:
        {context}

        Tasks:
        1. Explain in 2-3 sentences which tables are relevant and why.
        2. {"Generate a SQL query that answers the user's question." if include_sql else "Do not generate SQL."}

        Respond as JSON: {{"explanation": "...", "sql": "..."}}
        '''
        response = await self.gemini.generate(prompt)
        data = json.loads(response.text)
        return data["explanation"], data.get("sql")
        """
        # STUB — Phase 1
        explanation = (
            "Query engine is not yet connected to ChromaDB, Neo4j, or Gemini. "
            "Phase 2 will enable full AI-powered table discovery."
        )
        return explanation, None

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _to_response(self, r: RankedTable) -> QueryResultTable:
        return QueryResultTable(
            table_id=r.table_id,
            table_name=r.table_name,
            display_name=r.display_name,
            section=r.section_name,
            relevance_score=r.combined_score,
            matched_columns=r.matched_columns,
            match_reason=r.match_reason,
        )

    def _to_dict(self, r: RankedTable) -> dict:
        return {
            "table_id": str(r.table_id),
            "table_name": r.table_name,
            "section": r.section_name,
            "relevance_score": r.combined_score,
            "matched_columns": r.matched_columns,
            "match_reason": r.match_reason,
            "is_cross_section": r.is_cross_section,
        }

    def _build_gemini_context(self, results: list[RankedTable]) -> str:
        lines = []
        for r in results:
            line = f"- {r.table_name} (section: {r.section_name}, score: {r.combined_score})"
            if r.matched_columns:
                line += f"\n  Columns: {', '.join(r.matched_columns)}"
            lines.append(line)
        return "\n".join(lines)
