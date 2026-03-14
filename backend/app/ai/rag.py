"""
RAG: embed query and retrieve from vector store.
Uses Chroma in-memory; load documents separately to populate.
"""

from __future__ import annotations

import logging

from app.config import OPENAI_API_KEY
from app.models import embed

logger = logging.getLogger(__name__)

_store = None


def _get_client():
    import chromadb
    import os
    from chromadb.config import Settings
    global _store
    if _store is None:
        db_path = os.path.join(os.getcwd(), "chroma_db")
        _store = chromadb.PersistentClient(path=db_path, settings=Settings(anonymized_telemetry=False))
    return _store


def get_collection(name: str = "rag"):
    """Get or create the default RAG collection."""
    client = _get_client()
    return client.get_or_create_collection(name=name, metadata={"description": "RAG documents"})


def add_documents(texts: list[str], ids: list[str] | None = None, collection_name: str = "rag"):
    """Add documents to the vector store (embeds and stores)."""
    if not texts:
        return
    if ids is None:
        ids = [f"doc_{i}" for i in range(len(texts))]
    embeddings = [embed(t) for t in texts]
    if not any(embeddings):
        logger.warning("No embeddings; is OPENAI_API_KEY set?")
        return
    coll = get_collection(collection_name)
    coll.add(embeddings=embeddings, documents=texts, ids=ids[:len(texts)])


def retrieve(query: str, top_k: int = 4, collection_name: str = "rag") -> str:
    """
    Retrieve top_k documents for the query. Returns a single context string.
    If no collection or no API key, returns empty string.
    """
    if not OPENAI_API_KEY:
        return ""
    try:
        client = _get_client()
        coll = client.get_collection(name=collection_name)
    except Exception:
        return ""
    emb = embed(query)
    if not emb:
        return ""
    results = coll.query(query_embeddings=[emb], n_results=min(top_k, 20), include=["documents"])
    if not results or not results["documents"] or not results["documents"][0]:
        return ""
    return "\n\n".join(results["documents"][0])
