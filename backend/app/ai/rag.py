"""
RAG: embed query and retrieve from vector store.
Uses two DataStax Astra DBs:
- Agents RAG (guidelines): ASTRA_DB_* → sample_rag (ingest_sample.py)
- Orchestrator RAG (news):  ASTRA_DB_ORCHESTRATOR_* → news_rag (ingest_news.py)
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from app.config import (
    ASTRA_DB_API_ENDPOINT,
    ASTRA_DB_APPLICATION_TOKEN,
    ASTRA_DB_KEYSPACE,
    ASTRA_DB_ORCHESTRATOR_API_ENDPOINT,
    ASTRA_DB_ORCHESTRATOR_APPLICATION_TOKEN,
    ASTRA_DB_ORCHESTRATOR_KEYSPACE,
    ASTRA_EMBED_DIMENSION,
)
from app.models import embed

logger = logging.getLogger(__name__)

RAG_DB_AGENTS = "agents"
RAG_DB_ORCHESTRATOR = "orchestrator"
RAG_DB = Literal["agents", "orchestrator"]

_client = None
_databases: dict[str, Any] = {}


def _which_db_for_collection(collection_name: str) -> RAG_DB:
    """Use orchestrator DB for news_rag (and its dimension-suffixed names), agents DB for everything else."""
    if collection_name.startswith("news_rag"):
        return RAG_DB_ORCHESTRATOR
    return RAG_DB_AGENTS


def _get_client():
    global _client
    if _client is None:
        from astrapy import DataAPIClient
        _client = DataAPIClient()
    return _client


def _get_database(which: RAG_DB):
    global _databases
    if which not in _databases:
        if which == RAG_DB_ORCHESTRATOR:
            endpoint = ASTRA_DB_ORCHESTRATOR_API_ENDPOINT
            token = ASTRA_DB_ORCHESTRATOR_APPLICATION_TOKEN
            keyspace = ASTRA_DB_ORCHESTRATOR_KEYSPACE
            if not endpoint or not token:
                raise RuntimeError(
                    "Orchestrator Astra DB is not configured. "
                    "Set ASTRA_DB_ORCHESTRATOR_API_ENDPOINT and ASTRA_DB_ORCHESTRATOR_APPLICATION_TOKEN."
                )
        else:
            endpoint = ASTRA_DB_API_ENDPOINT
            token = ASTRA_DB_APPLICATION_TOKEN
            keyspace = ASTRA_DB_KEYSPACE
            if not endpoint or not token:
                raise RuntimeError(
                    "Agents Astra DB is not configured. Set ASTRA_DB_API_ENDPOINT and ASTRA_DB_APPLICATION_TOKEN."
                )
        client = _get_client()
        _databases[which] = client.get_database(endpoint, token=token, keyspace=keyspace)
    return _databases[which]


def _vector_definition(dimension: int | None = None):
    from astrapy.constants import VectorMetric
    from astrapy.info import CollectionDefinition, CollectionVectorOptions
    dim = dimension if dimension is not None else ASTRA_EMBED_DIMENSION
    return CollectionDefinition(
        vector=CollectionVectorOptions(
            dimension=dim,
            metric=VectorMetric.COSINE,
        ),
    )


def get_collection(name: str = "rag", embedding_dimension: int | None = None):
    """Get or create the RAG vector collection in the appropriate Astra DB.
    Which DB is inferred from name: news_rag* → orchestrator DB, else → agents DB.
    When creating a new collection, uses embedding_dimension if provided, else ASTRA_EMBED_DIMENSION.
    """
    which = _which_db_for_collection(name)
    db = _get_database(which)
    try:
        return db.create_collection(
            name, definition=_vector_definition(embedding_dimension)
        )
    except Exception as e:
        err = str(e).lower()
        if "already exists" in err or "exist" in err or "duplicate" in err:
            return db.get_collection(name)
        raise


def add_documents(
    texts: list[str],
    ids: list[str] | None = None,
    collection_name: str = "rag",
    metadatas: list[dict] | None = None,
) -> None:
    """Add documents to the vector store (embeds and stores). Uses agents DB for sample_rag*, orchestrator DB for news_rag*."""
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

    # Use actual embedding dimension so Astra collection matches the model (e.g. HF vs OpenAI).
    # Collection name is suffixed with dimension so different models don't conflict (e.g. rag_768 vs rag_1536).
    embedding_dim = len(v_embeddings[0])
    actual_name = f"{collection_name}_{embedding_dim}"
    coll = get_collection(actual_name, embedding_dimension=embedding_dim)
    documents = []
    for i, idx in enumerate(valid_idx):
        doc = {
            "_id": v_ids[i],
            "$vector": v_embeddings[i],
            "text": v_texts[i],
        }
        if v_metadatas and i < len(v_metadatas) and v_metadatas[i]:
            for k, v in v_metadatas[i].items():
                if k not in ("_id", "$vector", "text"):
                    doc[k] = v
        documents.append(doc)
    coll.insert_many(documents)


def retrieve_chunks(
    query: str,
    top_k: int = 4,
    collection_name: str = "rag",
    where_filter: dict | None = None,
) -> list[str]:
    """
    Retrieve top_k document chunks for the query (by vector similarity).
    Uses agents DB for sample_rag/rag*, orchestrator DB for news_rag*.
    Returns list of document text strings.
    Uses collection_name_{dimension} so it matches the collection used by add_documents for the same embed model.
    """
    which = _which_db_for_collection(collection_name)
    try:
        db = _get_database(which)
    except Exception as e:
        logger.debug("Astra get_database (%s) failed: %s", which, e)
        return []

    emb = embed(query)
    if not emb:
        return []

    actual_name = f"{collection_name}_{len(emb)}"
    try:
        coll = db.get_collection(actual_name)
    except Exception as e:
        logger.debug("Astra get_collection %s failed: %s", actual_name, e)
        return []

    filter_clause = where_filter if where_filter else {}
    limit = min(top_k, 1000)
    try:
        cursor = coll.find(
            filter=filter_clause,
            sort={"$vector": emb},
            limit=limit,
            projection={"text": True, "_id": False},
            include_similarity=True,
        )
        docs = cursor.to_list()
    except Exception as e:
        logger.warning("Astra find failed: %s", e)
        return []

    return [d["text"] for d in docs if d.get("text")]


def retrieve(
    query: str,
    top_k: int = 4,
    collection_name: str = "rag",
    where_filter: dict | None = None,
) -> str:
    """
    Retrieve top_k documents for the query. Returns a single context string.
    If Astra is not configured or no results, returns empty string.
    """
    chunks = retrieve_chunks(
        query,
        top_k=top_k,
        collection_name=collection_name,
        where_filter=where_filter,
    )
    return "\n\n".join(chunks) if chunks else ""
