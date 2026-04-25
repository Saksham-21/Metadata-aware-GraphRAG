"""
app/main.py
───────────
FastAPI application entry point.

Startup:
  uvicorn app.main:app --reload --port 8080

Swagger docs:
  http://localhost:8080/docs
ReDoc:
  http://localhost:8080/redoc
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api.v1 import auth, sections, tables, history, query, admin


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Code here runs on startup (before 'yield') and shutdown (after 'yield').
    Phase 2: initialise ChromaDB client, Neo4j driver, verify Gemini key.
    """
    # ── Startup ──
    print(f"🚀  {settings.PROJECT_NAME} starting — env={settings.APP_ENV}")
    # TODO Phase 2:
    # await init_chromadb()
    # await init_neo4j()
    yield
    # ── Shutdown ──
    print("🛑  Shutting down.")
    # TODO Phase 2:
    # await close_neo4j()


# ── App instance ──────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "Metadata-Aware GraphRAG Knowledge Base API.\n\n"
        "Combines semantic vector search (ChromaDB) and graph traversal (Neo4j) "
        "to help developers and BAs navigate thousands of database tables using "
        "natural language."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routers ───────────────────────────────────────────────────────────────────
PREFIX = settings.API_V1_PREFIX  # "/api/v1"

app.include_router(auth.router,      prefix=PREFIX)
app.include_router(sections.router,  prefix=PREFIX)
app.include_router(tables.router,    prefix=PREFIX)
app.include_router(history.router,   prefix=PREFIX)
app.include_router(query.router,     prefix=PREFIX)
app.include_router(admin.router,     prefix=PREFIX)


# ── Root & Health ─────────────────────────────────────────────────────────────
@app.get("/", tags=["Root"], include_in_schema=False)
async def root():
    return {
        "project": settings.PROJECT_NAME,
        "version": "1.0.0",
        "docs": "/docs",
        "env": settings.APP_ENV,
    }


@app.get("/ping", tags=["Root"])
async def ping():
    """Public health check — no auth required."""
    return {"status": "ok", "message": "pong"}


# ── Global exception handler ──────────────────────────────────────────────────
@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc: Exception):
    """
    Catch-all for unhandled exceptions.
    Returns a generic 500 instead of leaking stack traces in production.
    """
    if settings.APP_DEBUG:
        raise exc  # re-raise in dev so the traceback is visible
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please contact support."},
    )
