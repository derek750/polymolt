"""
RAG: embed query and retrieve from vector store.
Uses DataStax Astra DB (astrapy). Set ASTRA_DB_API_ENDPOINT and ASTRA_DB_APPLICATION_TOKEN.
"""

from __future__ import annotations

import logging

from app.config import (
    ASTRA_DB_API_ENDPOINT,
    ASTRA_DB_APPLICATION_TOKEN,
    ASTRA_DB_KEYSPACE,
    ASTRA_EMBED_DIMENSION,
)
from app.models import embed

logger = logging.getLogger(__name__)

_client = None
_database = None


def _get_client():
    global _client
    if _client is None:
        from astrapy import DataAPIClient
        _client = DataAPIClient()
    return _client


def _get_database():
    global _database
    if _database is None:
        if not ASTRA_DB_API_ENDPOINT or not ASTRA_DB_APPLICATION_TOKEN:
            raise RuntimeError(
                "Astra DB is not configured. Set ASTRA_DB_API_ENDPOINT and ASTRA_DB_APPLICATION_TOKEN."
            )
        client = _get_client()
        _database = client.get_database(
            ASTRA_DB_API_ENDPOINT,
            token=ASTRA_DB_APPLICATION_TOKEN,
            keyspace=ASTRA_DB_KEYSPACE,
        )
    return _database


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
    """Get or create the RAG vector collection in Astra DB.
    When creating a new collection, uses embedding_dimension if provided, else ASTRA_EMBED_DIMENSION.
    """
    db = _get_database()
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
    Returns list of document text strings.
    Uses collection_name_{dimension} so it matches the collection used by add_documents for the same embed model.
    """
    try:
        db = _get_database()
    except Exception as e:
        logger.debug("Astra get_database failed: %s", e)
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
