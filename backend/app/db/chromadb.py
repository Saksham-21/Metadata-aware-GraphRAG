"""
app/db/chromadb.py
──────────────────
ChromaDB PersistentClient — embedded, file-based vector store.

We use PersistentClient (no separate Docker container needed).
Embeddings are stored on disk at CHROMA_PERSIST_DIR (default: ./chroma_data).

Collections are created automatically on first use.
"""

import logging

import chromadb
from chromadb import Collection

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: chromadb.ClientAPI | None = None


def get_chroma_client() -> chromadb.ClientAPI:
    """
    Return the singleton ChromaDB PersistentClient.
    Creates the client on first call; reuses it thereafter.
    """
    global _client
    if _client is None:
        logger.info("Initialising ChromaDB PersistentClient at '%s'", settings.CHROMA_PERSIST_DIR)
        _client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
    return _client


def get_tables_collection() -> Collection:
    """
    Return the tables embedding collection, creating it if it does not exist.

    Collection settings:
      - hnsw:space = cosine   → distances are in [0, 1], similarity = 1 - distance
      - ChromaDB auto-embeds documents using its default all-MiniLM-L6-v2 model
        unless an external embedding function is supplied.
    """
    collection_name = f"{settings.CHROMA_COLLECTION_PREFIX}_tables"
    return get_chroma_client().get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def reset_chroma_client() -> None:
    """Force re-initialisation of the ChromaDB client (useful for testing)."""
    global _client
    _client = None
