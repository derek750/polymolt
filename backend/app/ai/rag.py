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
    """
    Add documents to the vector store. 
    If external embeddings fail, falls back to Chroma's local embedding engine.
    """
    if not texts:
        return
    if ids is None:
        ids = [f"doc_{i}" for i in range(len(texts))]
    
    # Try to get external embeddings
    embeddings = [e for e in (embed(t) for t in texts) if e]
    coll = get_collection(collection_name)
    
    if len(embeddings) == len(texts):
        # Successfully got all embeddings from API
        coll.add(embeddings=embeddings, documents=texts, ids=ids[:len(texts)])
    else:
        # Fallback: Let Chroma handle its own embeddings locally
        logger.info("External embeddings failed; using Chroma's built-in local embeddings.")
        coll.add(documents=texts, ids=ids[:len(texts)])


def retrieve_chunks(query: str, top_k: int = 4, collection_name: str = "rag") -> list[str]:
    """
    Retrieve top_k documents for the query. Returns a single context string.
    Falls back to local query_texts if external embeddings fail.
    """
    try:
        client = _get_client()
        coll = client.get_collection(name=collection_name)
    except Exception:
        return ""

    emb = embed(query)
    
    if emb:
        # Use external embeddings if successful
        results = coll.query(query_embeddings=[emb], n_results=min(top_k, 20), include=["documents"])
    else:
        # Fallback: Query using raw text (Chroma will embed locally)
        results = coll.query(query_texts=[query], n_results=min(top_k, 20), include=["documents"])
        
    if not results or not results["documents"] or not results["documents"][0]:
        return []
    return list(results["documents"][0])


def retrieve(query: str, top_k: int = 4, collection_name: str = "rag") -> str:
    """
    Retrieve top_k documents for the query. Returns a single context string.
    If no collection or no API key, returns empty string.
    """
    chunks = retrieve_chunks(query, top_k=top_k, collection_name=collection_name)
    return "\n\n".join(chunks) if chunks else ""
