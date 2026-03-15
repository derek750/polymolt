"""
Upstash Redis caching layer.

Three cache tiers:
1. Embedding cache   — deterministic text→vector, 24h TTL
2. RAG caches        — exact-match + semantic vector cache, 1h TTL
3. DB read cache     — query results, 5m TTL

The *vector cache* (tier 2b) stores query embeddings alongside their Astra DB
results.  On a new query it computes cosine similarity against every cached
embedding for the same collection/top_k/filter.  If the best match exceeds
VECTOR_CACHE_SIMILARITY_THRESHOLD (default 0.97) the cached chunks are returned
without hitting Astra DB at all.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
from typing import Any

from app.config import UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN

logger = logging.getLogger(__name__)

_redis = None

# TTL constants (seconds)
TTL_EMBEDDING = 86_400      # 24h — embeddings are deterministic for same input
TTL_RAG_RETRIEVAL = 3_600   # 1h  — stale after new documents ingested
TTL_DB_READ = 300           # 5m  — stale after DB writes

# Vector-cache tuning
VECTOR_CACHE_SIMILARITY_THRESHOLD = 0.97   # cosine sim required for a hit
VECTOR_CACHE_MAX_ENTRIES = 50              # per collection/top_k/filter combo

# Namespace constants
NS_EMBEDDING = "embed"
NS_RAG = "rag"
NS_VCACHE = "vcache"
NS_DB = "db"


def get_redis():
    """Lazy-init the Upstash Redis client (singleton)."""
    global _redis
    if _redis is None:
        if not UPSTASH_REDIS_REST_URL or not UPSTASH_REDIS_REST_TOKEN:
            raise RuntimeError(
                "Upstash Redis not configured. "
                "Set UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN."
            )
        from upstash_redis import Redis
        _redis = Redis(url=UPSTASH_REDIS_REST_URL, token=UPSTASH_REDIS_REST_TOKEN)
    return _redis


def _make_key(namespace: str, *parts: Any) -> str:
    """Deterministic cache key: namespace:sha256(json(parts))."""
    raw = json.dumps(parts, sort_keys=True, default=str)
    digest = hashlib.sha256(raw.encode()).hexdigest()[:32]
    return f"{namespace}:{digest}"


def cache_get(namespace: str, *key_parts: Any) -> Any | None:
    """Fetch from cache.  Returns None on miss or any error."""
    try:
        r = get_redis()
        key = _make_key(namespace, *key_parts)
        val = r.get(key)
        if val is None:
            return None
        return json.loads(val) if isinstance(val, str) else val
    except Exception as e:
        logger.debug("cache_get(%s) error: %s", namespace, e)
        return None


def cache_set(namespace: str, *key_parts: Any, value: Any, ttl: int) -> None:
    """Write to cache with TTL (seconds).  Fails silently."""
    try:
        r = get_redis()
        key = _make_key(namespace, *key_parts)
        r.set(key, json.dumps(value, default=str), ex=ttl)
    except Exception as e:
        logger.debug("cache_set(%s) error: %s", namespace, e)


def cache_delete(namespace: str, *key_parts: Any) -> None:
    """Delete a single cache entry.  Fails silently."""
    try:
        r = get_redis()
        key = _make_key(namespace, *key_parts)
        r.delete(key)
    except Exception as e:
        logger.debug("cache_delete(%s) error: %s", namespace, e)


def cache_invalidate_namespace(namespace: str) -> int:
    """Delete ALL keys under a namespace using SCAN.  Returns count deleted."""
    deleted = 0
    try:
        r = get_redis()
        cursor: int = 0
        while True:
            cursor, keys = r.scan(cursor, match=f"{namespace}:*", count=200)
            if keys:
                for key in keys:
                    r.delete(key)
                    deleted += 1
            if cursor == 0:
                break
    except Exception as e:
        logger.debug("cache_invalidate_namespace(%s) error: %s", namespace, e)
    return deleted


def cache_invalidate_rag(collection_name: str | None = None) -> int:
    """Invalidate RAG retrieval cache.

    If collection_name given, only invalidates keys for that collection
    (by scanning for the sub-prefix).  Otherwise clears the full NS_RAG namespace.
    """
    prefix = f"{NS_RAG}:{collection_name}" if collection_name else NS_RAG
    deleted = 0
    try:
        r = get_redis()
        cursor: int = 0
        while True:
            cursor, keys = r.scan(cursor, match=f"{prefix}*", count=200)
            if keys:
                for key in keys:
                    r.delete(key)
                    deleted += 1
            if cursor == 0:
                break
    except Exception as e:
        logger.debug("cache_invalidate_rag(%s) error: %s", collection_name, e)
    return deleted


def _rag_key(collection_name: str, *extra: Any) -> str:
    """Build a RAG cache key that starts with NS_RAG:collection_name: so
    collection-scoped invalidation works correctly."""
    raw = json.dumps(extra, sort_keys=True, default=str)
    digest = hashlib.sha256(raw.encode()).hexdigest()[:32]
    return f"{NS_RAG}:{collection_name}:{digest}"


def rag_cache_get(collection_name: str, *extra: Any) -> Any | None:
    """RAG-specific cache get (keys are namespaced by collection)."""
    try:
        r = get_redis()
        key = _rag_key(collection_name, *extra)
        val = r.get(key)
        if val is None:
            return None
        return json.loads(val) if isinstance(val, str) else val
    except Exception as e:
        logger.debug("rag_cache_get(%s) error: %s", collection_name, e)
        return None


def rag_cache_set(collection_name: str, *extra: Any, value: Any, ttl: int) -> None:
    """RAG-specific cache set (keys are namespaced by collection)."""
    try:
        r = get_redis()
        key = _rag_key(collection_name, *extra)
        r.set(key, json.dumps(value, default=str), ex=ttl)
    except Exception as e:
        logger.debug("rag_cache_set(%s) error: %s", collection_name, e)


# ── Semantic vector cache ────────────────────────────────────────────────
#
# Stores (embedding, chunks) pairs in a Redis hash keyed by
#   vcache:{collection}:{top_k}:{filter_hash}
# On lookup we HGETALL the hash, compute cosine similarity of the new
# query embedding against every cached embedding, and return the chunks
# for the best match if similarity >= threshold.
#
# Embeddings are stored at reduced precision (4 decimals) to keep the
# hash small.  50 entries × 768-dim ≈ 250 KB per HGETALL — well within
# Upstash's 1 MB response limit.

def _cosine_sim(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors of equal length."""
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _vcache_hash_key(collection: str, top_k: int, where_filter: dict | None) -> str:
    fh = hashlib.sha256(
        json.dumps(where_filter, sort_keys=True, default=str).encode()
    ).hexdigest()[:12] if where_filter else "none"
    return f"{NS_VCACHE}:{collection}:{top_k}:{fh}"


def _compact_embedding(emb: list[float]) -> list[float]:
    """Round to 4 decimals to save ~40 % storage in JSON."""
    return [round(v, 4) for v in emb]


def vector_cache_lookup(
    collection_name: str,
    query_embedding: list[float],
    top_k: int,
    where_filter: dict | None = None,
) -> list[str] | None:
    """Semantic cache lookup.

    Scans cached embeddings for the same collection/top_k/filter and
    returns the stored chunks if cosine similarity >= threshold.
    Returns None on miss.
    """
    try:
        r = get_redis()
        hkey = _vcache_hash_key(collection_name, top_k, where_filter)
        raw: dict[str, str] = r.hgetall(hkey)
        if not raw:
            return None

        best_sim = 0.0
        best_chunks: list[str] | None = None

        for _entry_id, entry_json in raw.items():
            entry = json.loads(entry_json) if isinstance(entry_json, str) else entry_json
            cached_emb = entry.get("e")
            if not cached_emb or len(cached_emb) != len(query_embedding):
                continue
            sim = _cosine_sim(query_embedding, cached_emb)
            if sim > best_sim:
                best_sim = sim
                best_chunks = entry.get("c")

        if best_sim >= VECTOR_CACHE_SIMILARITY_THRESHOLD and best_chunks is not None:
            logger.info(
                "Vector cache HIT (sim=%.4f) collection=%s",
                best_sim, collection_name,
            )
            return best_chunks
        return None
    except Exception as e:
        logger.debug("vector_cache_lookup error: %s", e)
        return None


def vector_cache_store(
    collection_name: str,
    query_embedding: list[float],
    top_k: int,
    where_filter: dict | None,
    chunks: list[str],
) -> None:
    """Persist a query embedding + its result chunks in the vector cache."""
    try:
        r = get_redis()
        hkey = _vcache_hash_key(collection_name, top_k, where_filter)

        emb_sample = ",".join(f"{v:.6f}" for v in query_embedding[:32])
        entry_id = hashlib.sha256(emb_sample.encode()).hexdigest()[:16]

        entry = {"e": _compact_embedding(query_embedding), "c": chunks}
        r.hset(hkey, entry_id, json.dumps(entry, default=str))
        r.expire(hkey, TTL_RAG_RETRIEVAL)

        size = r.hlen(hkey)
        if size > VECTOR_CACHE_MAX_ENTRIES:
            all_keys = r.hkeys(hkey)
            for k in all_keys[: size - VECTOR_CACHE_MAX_ENTRIES]:
                r.hdel(hkey, k)
    except Exception as e:
        logger.debug("vector_cache_store error: %s", e)


def vector_cache_invalidate(collection_name: str | None = None) -> int:
    """Delete all vector-cache hashes for a collection (or all collections)."""
    prefix = f"{NS_VCACHE}:{collection_name}" if collection_name else NS_VCACHE
    deleted = 0
    try:
        r = get_redis()
        cursor: int = 0
        while True:
            cursor, keys = r.scan(cursor, match=f"{prefix}*", count=200)
            if keys:
                for key in keys:
                    r.delete(key)
                    deleted += 1
            if cursor == 0:
                break
    except Exception as e:
        logger.debug("vector_cache_invalidate(%s) error: %s", collection_name, e)
    return deleted


# ── Health ───────────────────────────────────────────────────────────────

def redis_health() -> dict[str, Any]:
    """Quick health check: PING + key count."""
    try:
        r = get_redis()
        pong = r.ping()
        info = r.dbsize()
        return {"status": "ok", "ping": pong, "key_count": info}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
