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


def add_documents(texts: list[str], ids: list[str] | None = None, collection_name: str = "rag", metadatas: list[dict] | None = None):
    """Add documents to the vector store (embeds and stores)."""
    if not texts:
        return
    if ids is None:
        ids = [f"doc_{i}" for i in range(len(texts))]

    all_embeddings = [embed(t) for t in texts]

    valid_idx = [i for i, e in enumerate(all_embeddings) if e]
    if not valid_idx:
        raise ValueError(
            "Embedding failed for all documents. "
            "Check that OPENAI_API_KEY or GOOGLE_API_KEY is set."
        )

    v_embeddings = [all_embeddings[i] for i in valid_idx]
    v_texts = [texts[i] for i in valid_idx]
    v_ids = [ids[i] for i in valid_idx]
    v_metadatas = [metadatas[i] for i in valid_idx] if metadatas else None

    coll = get_collection(collection_name)
    coll.add(embeddings=v_embeddings, documents=v_texts, ids=v_ids, metadatas=v_metadatas)


def retrieve_chunks(query: str, top_k: int = 4, collection_name: str = "rag", where_filter: dict | None = None) -> list[str]:
    """
    Retrieve top_k documents for the query. Returns a single context string.
    Falls back to local query_texts if external embeddings fail.
    """
    try:
        client = _get_client()
        coll = client.get_collection(name=collection_name)
    except Exception:
        return []

    emb = embed(query)
    if not emb:
        return []
        
    query_kwargs = {
        "query_embeddings": [emb],
        "n_results": min(top_k, 20),
        "include": ["documents"]
    }
    if where_filter:
        query_kwargs["where"] = where_filter
        
    results = coll.query(**query_kwargs)
    if not results or not results["documents"] or not results["documents"][0]:
        return []
    return list(results["documents"][0])


def retrieve(query: str, top_k: int = 4, collection_name: str = "rag", where_filter: dict | None = None) -> str:
    """
    Retrieve top_k documents for the query. Returns a single context string.
    If no collection or no API key, returns empty string.
    """
    chunks = retrieve_chunks(query, top_k=top_k, collection_name=collection_name, where_filter=where_filter)
    return "\n\n".join(chunks) if chunks else ""
