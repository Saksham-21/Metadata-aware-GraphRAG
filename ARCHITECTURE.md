# Metadata-Aware GraphRAG Chatbot — Full System Architecture

> **Stack:** FastAPI · Next.js · ChromaDB · Neo4j · Gemini API · PostgreSQL (metadata store)
> **Version:** v1.0 — April 2026

---

## 1. System Overview

This system is a **web-based Knowledge Base platform** for large organisations with thousands of database tables. It allows Developers and Business Analysts to ingest, manage, and query table/column metadata intelligently — combining semantic vector search (ChromaDB) and graph-based relationship traversal (Neo4j) to return accurate, context-aware results.

```
┌─────────────────────────────────────────────────────────────┐
│                        Next.js Frontend                      │
│  Login | Ingestion | Query | History | Sections | Admin      │
└────────────────────────┬────────────────────────────────────┘
                         │ REST / HTTP
┌────────────────────────▼────────────────────────────────────┐
│                      FastAPI Backend                         │
│  Auth · Ingestion · Query Engine · History · Sections        │
└──────┬──────────────────┬───────────────────┬───────────────┘
       │                  │                   │
┌──────▼──────┐  ┌────────▼──────┐  ┌────────▼──────────────┐
│ PostgreSQL  │  │   ChromaDB    │  │        Neo4j           │
│ (Source of  │  │ (Semantic     │  │  (Relationship Graph   │
│  Truth)     │  │  Search)      │  │   + Section Graph)     │
└─────────────┘  └───────────────┘  └────────────────────────┘
                         │
               ┌─────────▼──────────┐
               │    Gemini API       │
               │  (LLM Reasoning)    │
               └────────────────────┘
```

---

## 2. ChromaDB vs Neo4j — Responsibility Split

This is the most critical architectural decision. Each database does what it is best at.

### ChromaDB — "What does this table/column mean?"
ChromaDB handles **semantic similarity search**. It stores embedded vector representations of your metadata so the system can find tables/columns that are *semantically close* to a user's natural language question, even if the exact words don't match.

**Stores:**
- Table name + description embeddings
- Column name + description + data type embeddings
- Business glossary terms linked to tables/columns
- Section tags on each document

**Answers questions like:**
- "Which tables are about customer credit risk?"
- "Find columns that store transaction amounts"
- "What tables relate to loan disbursement?"

**Embedding model:** `models/embedding-001` (Google) or `text-embedding-3-small` (OpenAI)

---

### Neo4j — "How are these tables connected to each other?"
Neo4j handles **structural and relational knowledge**. It models tables as nodes and their relationships (foreign keys, shared business domains, section membership) as edges.

**Stores:**
- `(:Table)` nodes with properties: `id`, `name`, `section`, `created_by`
- `(:Column)` nodes with properties: `name`, `type`, `description`
- `(:Section)` nodes: `credit_card`, `customer_loan`, etc.
- `[:HAS_COLUMN]` edges: Table → Column
- `[:REFERENCES]` edges: Table A → Table B (foreign key)
- `[:BELONGS_TO]` edges: Table → Section
- `[:RELATED_TO]` edges: manually curated business relationships

**Answers questions like:**
- "If I need `credit_card_txn`, what other tables do I also need to JOIN?"
- "Which tables from `customer_profile` section are linked to this credit card table?"
- "Give me the full join path from `customer` to `repayment_schedule`"

---

### How They Work Together (The Query Pipeline)

```
User Question (NL)
        │
        ▼
[1] Section Filter Applied (if user selected a section)
        │
        ▼
[2] ChromaDB Semantic Search → Top-K matching tables (e.g., top 15)
        │
        ▼
[3] Neo4j Graph Expansion → Traverse relationships from those 15 tables
    → Pull in linked tables from same or connected sections
    → Cross-section expansion happens here when graph edges exist
        │
        ▼
[4] Merge & Rank → Deduplicate, score by: semantic score + graph hop distance
        │
        ▼
[5] Gemini API → Given ranked tables/columns + user question,
    generate: suggested tables, relevant columns, optional SQL
        │
        ▼
[6] Response to user: table list, column list, SQL (if requested)
```

---

## 3. Sections Architecture

Sections divide the knowledge base into business domains for better precision.

**Examples:** `credit_card`, `customer_loan`, `deposits`, `customer_profile`, `risk_management`

### How Sections Work
- Every table **belongs to one primary section** (set during ingestion)
- A table **can have secondary sections** (e.g., `customer_profile` table is in both `customer_profile` and `credit_card` sections)
- Sections exist as nodes in **Neo4j** (`[:BELONGS_TO]` edges)
- Sections are stored as **metadata filters** in **ChromaDB** (`where={"section": "credit_card"}`)

### Cross-Section Search (Option B — Auto-Expand via Graph)
1. User selects section: `credit_card`
2. ChromaDB searches only within `credit_card` section first
3. If top results have Neo4j `[:REFERENCES]` edges pointing to tables in other sections (e.g., `customer_profile`), those are auto-included
4. Final response shows: primary results (credit_card) + expanded results (other sections), clearly labelled

---

## 4. Role-Based Access Control (RBAC)

| Role | Permissions |
|------|-------------|
| **Admin** | Register new users, assign roles, manage sections, view all history, full ingestion access |
| **Developer** | Ingest tables, edit tables, view history, query |
| **BA (Business Analyst)** | Edit table/column descriptions, view history, query (cannot add/delete tables) |
| **Viewer** *(optional future)* | Query only, read-only history |

### Key Rules
- Only **Admin** can call `POST /auth/register`
- **Developers** can create/delete tables and columns
- **BAs** can only update descriptions/business terms — cannot rename tables or delete columns
- All users have **their own query history** (private)
- Ingestion and edit history is **global** (visible to all based on role)

---

## 5. Data Models (PostgreSQL — Source of Truth)

PostgreSQL is the primary source of truth. ChromaDB and Neo4j are derived indexes built from PostgreSQL data.

### `users`
```sql
id UUID PRIMARY KEY
name VARCHAR
email VARCHAR UNIQUE
password_hash VARCHAR
role ENUM('admin', 'developer', 'ba', 'viewer')
created_at TIMESTAMP
created_by UUID REFERENCES users(id)  -- who registered this user
is_active BOOLEAN DEFAULT TRUE
```

### `sections`
```sql
id UUID PRIMARY KEY
name VARCHAR UNIQUE          -- e.g., 'credit_card'
display_name VARCHAR         -- e.g., 'Credit Card'
description TEXT
created_by UUID REFERENCES users(id)
created_at TIMESTAMP
```

### `tables`
```sql
id UUID PRIMARY KEY
table_name VARCHAR UNIQUE    -- globally unique across org
display_name VARCHAR
description TEXT
primary_section_id UUID REFERENCES sections(id)
tags TEXT[]
created_by UUID REFERENCES users(id)
created_at TIMESTAMP
updated_at TIMESTAMP
is_active BOOLEAN DEFAULT TRUE
```

### `table_sections` (many-to-many for secondary sections)
```sql
table_id UUID REFERENCES tables(id)
section_id UUID REFERENCES sections(id)
PRIMARY KEY (table_id, section_id)
```

### `columns`
```sql
id UUID PRIMARY KEY
table_id UUID REFERENCES tables(id)
column_name VARCHAR
data_type VARCHAR
description TEXT
is_nullable BOOLEAN
is_primary_key BOOLEAN
is_foreign_key BOOLEAN
fk_references_table_id UUID REFERENCES tables(id)  -- if FK
fk_references_column VARCHAR
business_term VARCHAR        -- business glossary term
sample_values TEXT[]
created_by UUID REFERENCES users(id)
created_at TIMESTAMP
updated_at TIMESTAMP
is_active BOOLEAN DEFAULT TRUE
```

### `edit_history`
```sql
id UUID PRIMARY KEY
entity_type ENUM('table', 'column', 'section')
entity_id UUID
action ENUM('create', 'update', 'delete')
changed_by UUID REFERENCES users(id)
changed_at TIMESTAMP
before_state JSONB           -- full snapshot before edit
after_state JSONB            -- full snapshot after edit
change_summary TEXT          -- human-readable: "Updated description of col X"
```

### `query_history`
```sql
id UUID PRIMARY KEY
user_id UUID REFERENCES users(id)   -- per-user, private
question TEXT
section_filter VARCHAR               -- which section was selected
result_tables JSONB                  -- returned table suggestions
generated_sql TEXT                   -- if SQL was generated
feedback ENUM('positive','negative','none') DEFAULT 'none'
created_at TIMESTAMP
```

---

## 6. FastAPI — Full API Route Map

### Auth Routes
```
POST   /api/v1/auth/register        → Admin only — create new user
POST   /api/v1/auth/login           → All — returns JWT token
POST   /api/v1/auth/logout          → All — invalidate token
GET    /api/v1/auth/me              → All — get current user profile
PATCH  /api/v1/auth/users/{id}      → Admin — update user role / activate / deactivate
GET    /api/v1/auth/users           → Admin — list all users
```

### Sections Routes (GLOBAL scope)
```
GET    /api/v1/sections             → All — list all sections
POST   /api/v1/sections             → Admin — create new section
PATCH  /api/v1/sections/{id}        → Admin — update section
DELETE /api/v1/sections/{id}        → Admin — soft delete section
```

### Ingestion Routes (GLOBAL scope)
```
POST   /api/v1/tables               → Developer — add new table with columns
GET    /api/v1/tables               → All — list all tables (paginated, filterable by section)
GET    /api/v1/tables/{id}          → All — get full table detail (with columns)
PATCH  /api/v1/tables/{id}          → Developer/BA — update table metadata
DELETE /api/v1/tables/{id}          → Developer — soft delete table

POST   /api/v1/tables/{id}/columns          → Developer — add column to table
PATCH  /api/v1/tables/{id}/columns/{col_id} → Developer/BA — update column
DELETE /api/v1/tables/{id}/columns/{col_id} → Developer — remove column

POST   /api/v1/tables/{id}/sections         → Developer — add table to secondary section
DELETE /api/v1/tables/{id}/sections/{sec_id}→ Developer — remove table from section
```

### History Routes (GLOBAL scope — role filtered)
```
GET    /api/v1/history              → All — paginated global edit history
                                      Query params: entity_type, entity_id, user_id,
                                                    from_date, to_date, action
GET    /api/v1/history/{id}         → All — single history entry (shows before/after)
```

### Query Routes (PER-USER scope)
```
POST   /api/v1/query                → All — submit NL question
                                      Body: { question, section_id (optional),
                                              include_sql: bool }
                                      Returns: matched tables, columns,
                                               cross-section expansions, SQL

GET    /api/v1/query/history        → All — get current user's query history (private)
GET    /api/v1/query/history/{id}   → All — single past query result
PATCH  /api/v1/query/history/{id}/feedback → All — submit positive/negative feedback
DELETE /api/v1/query/history        → All — clear own query history
```

### Admin Routes
```
GET    /api/v1/admin/stats          → Admin — system stats (table count, user count, queries today)
POST   /api/v1/admin/reindex        → Admin — force re-sync PostgreSQL → ChromaDB + Neo4j
GET    /api/v1/admin/health         → Admin — health check all services
```

---

## 7. Ingestion Flow (How Knowledge Base Gets Updated)

When a Developer adds or edits a table, the system updates **all three stores** atomically.

```
Developer submits table data via UI
          │
          ▼
[1] Validate: table_name unique? columns valid? section exists?
          │
          ▼
[2] PostgreSQL: INSERT/UPDATE tables + columns
          │
          ▼
[3] History: Snapshot before_state → after_state → save to edit_history
          │
          ├──────────────────────────────────────────┐
          ▼                                          ▼
[4a] ChromaDB: Upsert embeddings           [4b] Neo4j: Upsert (:Table) node
    - Embed: table_name + description            - Create/update (:Column) nodes
    - Embed: each column name + desc             - Create [:HAS_COLUMN] edges
    - Tag with section metadata                  - Create [:BELONGS_TO] section edges
    - Tag with column types, business terms      - Create [:REFERENCES] FK edges
          │                                          │
          └──────────────────┬───────────────────────┘
                             ▼
                    [5] Return success + updated table to UI
```

**On Delete:** Soft-delete in PostgreSQL, remove from ChromaDB collection, mark node inactive in Neo4j (do not delete — preserve graph history).

---

## 8. History Tracking Design

History is stored in the `edit_history` table in PostgreSQL. Each row captures a **full before/after JSON snapshot** of the entity that changed.

**Example history entry for a column description update:**
```json
{
  "id": "abc-123",
  "entity_type": "column",
  "entity_id": "col-456",
  "action": "update",
  "changed_by": { "id": "user-789", "name": "Ravi K", "role": "developer" },
  "changed_at": "2026-04-15T10:32:00Z",
  "change_summary": "Updated description of column 'txn_amount' in table 'credit_card_txn'",
  "before_state": {
    "column_name": "txn_amount",
    "description": "Amount of transaction",
    "data_type": "DECIMAL"
  },
  "after_state": {
    "column_name": "txn_amount",
    "description": "Transaction amount in INR, inclusive of GST and surcharges",
    "data_type": "DECIMAL"
  }
}
```

**Key rules:**
- No rollback functionality — history is read-only audit trail
- All roles can **view** history (GET endpoints)
- Only the history of global ingestion changes (tables/columns/sections) is public
- Query history is **strictly per-user private**

---

## 9. Query Flow — Detailed

```
POST /api/v1/query
Body: {
  "question": "Which tables hold credit card transaction data and link to customer info?",
  "section_id": "credit_card",   ← optional
  "include_sql": true
}
```

**Step-by-step pipeline:**

```
[1] Extract intent keywords using Gemini
    → "credit card transactions", "customer info", "linking tables"

[2] ChromaDB Search (section-filtered if section_id provided)
    → Filter: where={"section": "credit_card"}
    → Semantic search → Top 15 table candidates with scores

[3] Neo4j Graph Expansion
    → For each of the 15 tables:
      MATCH (t:Table)-[:REFERENCES|RELATED_TO*1..2]-(related)
      WHERE related.is_active = true
    → Collect related tables from other sections (e.g., customer_profile)
    → Annotate each with: hop_distance, relationship_type, source_section

[4] Merge + Score
    → Combined score = (0.6 × semantic_score) + (0.4 × 1/hop_distance)
    → Deduplicate, sort by score, keep top 20

[5] Gemini Final Reasoning
    Prompt includes:
    - User question
    - Top 20 tables with columns and descriptions
    - Relationship context from Neo4j
    - Instruction: suggest tables, relevant columns, and generate SQL if asked

[6] Response
{
  "question": "...",
  "primary_results": [
    { "table": "credit_card_txn", "relevance": 0.94, "section": "credit_card",
      "matched_columns": ["txn_id", "txn_amount", "customer_id"], "match_reason": "..." }
  ],
  "cross_section_expansions": [
    { "table": "customer_master", "relevance": 0.81, "section": "customer_profile",
      "linked_via": "credit_card_txn.customer_id → customer_master.customer_id" }
  ],
  "suggested_sql": "SELECT ct.txn_id, ct.txn_amount, cm.customer_name ...",
  "explanation": "The credit_card_txn table holds transaction records. It links to customer_master via customer_id..."
}
```

---

## 10. Frontend Pages (Next.js)

| Page | Route | Access |
|------|-------|--------|
| Login | `/login` | Public |
| Dashboard | `/` | All |
| Ingestion — Add Table | `/ingest/new` | Developer |
| Ingestion — Edit Table | `/ingest/{id}` | Developer, BA |
| Tables Browser | `/tables` | All |
| Table Detail | `/tables/{id}` | All |
| Query Chat | `/query` | All |
| Query History | `/query/history` | All (own history) |
| Edit History | `/history` | All |
| History Detail | `/history/{id}` | All |
| Sections Manager | `/admin/sections` | Admin |
| User Management | `/admin/users` | Admin |
| System Health | `/admin/health` | Admin |

---

## 11. Key Technology Choices Summary

| Component | Technology | Why |
|-----------|-----------|-----|
| Backend API | FastAPI (Python) | Async, fast, auto-docs, easy Gemini/ChromaDB/Neo4j integration |
| Frontend | Next.js | SSR for SEO, API routes, great DX |
| Primary DB | PostgreSQL | Source of truth, ACID, JSONB for history snapshots |
| Vector DB | ChromaDB | Easy to self-host, Python-native, metadata filtering support |
| Graph DB | Neo4j | Industry standard for relationship graphs, Cypher queries |
| LLM | Gemini API (gemini-1.5-pro) | Strong reasoning, large context window for many table descriptions |
| Auth | JWT + bcrypt | Stateless, role claims in token |
| ORM | SQLAlchemy + Alembic | Migrations, type safety |
| Neo4j Client | `neo4j` Python driver | Official driver |
| ChromaDB Client | `chromadb` Python SDK | Official SDK |

---

## 12. Folder Structure

```
project/
├── backend/                     ← FastAPI
│   ├── app/
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── auth.py
│   │   │   │   ├── tables.py
│   │   │   │   ├── columns.py
│   │   │   │   ├── sections.py
│   │   │   │   ├── history.py
│   │   │   │   ├── query.py
│   │   │   │   └── admin.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py      ← JWT, RBAC decorators
│   │   │   └── dependencies.py
│   │   ├── db/
│   │   │   ├── postgres.py      ← SQLAlchemy session
│   │   │   ├── chromadb.py      ← ChromaDB client + upsert helpers
│   │   │   └── neo4j.py         ← Neo4j driver + Cypher helpers
│   │   ├── models/              ← SQLAlchemy ORM models
│   │   ├── schemas/             ← Pydantic request/response models
│   │   ├── services/
│   │   │   ├── ingestion.py     ← Orchestrates PG + Chroma + Neo4j on ingest
│   │   │   ├── query_engine.py  ← Full query pipeline (steps 1-6)
│   │   │   ├── history.py       ← History snapshot logic
│   │   │   └── gemini.py        ← Gemini API wrapper
│   │   └── main.py
│   ├── alembic/                 ← DB migrations
│   └── requirements.txt
│
└── frontend/                    ← Next.js
    ├── app/
    │   ├── (auth)/login/
    │   ├── (dashboard)/
    │   ├── ingest/
    │   ├── tables/
    │   ├── query/
    │   ├── history/
    │   └── admin/
    ├── components/
    │   ├── TableForm/           ← Add/edit table + columns UI
    │   ├── QueryChat/           ← Chat interface with section selector
    │   ├── HistoryViewer/       ← Before/after diff display
    │   └── SectionBadge/
    └── lib/
        └── api.ts               ← Typed API client
```

---

## 13. Next Steps (Recommended Build Order)

1. **PostgreSQL schema + Alembic migrations** — source of truth first
2. **Auth system** — JWT, RBAC, admin-only register
3. **Ingestion API** — POST/PATCH tables + columns → syncs PG + ChromaDB + Neo4j
4. **History capture** — hook into every write operation
5. **Sections API** — CRUD for sections
6. **Query Engine** — ChromaDB search → Neo4j expansion → Gemini reasoning
7. **Next.js frontend** — Ingestion UI, Query Chat, History viewer
8. **Admin panel** — User management, health dashboard, manual reindex

---

*This document reflects the full architecture as discussed. Ready to begin implementation on any module.*
