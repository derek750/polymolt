"""
Centralized AI model access.

Usage:
    from app.models import generate, embed

generate() defaults to OpenAI (or compatible proxy) unless the model name
starts with "gemini", in which case it routes to the Gemini provider.

embed() always uses Gemini — the OpenAI-compatible proxy (HuggingFace
Inference Endpoints) does not expose an /embeddings route.
Embedding results are cached in Upstash Redis (deterministic for same input).
"""

from __future__ import annotations

import logging

from app.config import CHAT_MODEL, DEFAULT_MODEL_NO_TOKENS, GOOGLE_API_KEY
from app.models import openai as _openai  # kept for compatibility, but not used by default
from app.models import gemini as _gemini

_log = logging.getLogger(__name__)


def _is_gemini(model: str) -> bool:
    return model.strip().lower().startswith("gemini")


def generate(
    user_prompt: str,
    *,
    system_prompt: str | None = None,
    model: str | None = None,
    max_tokens: int = 1024,
    json_mode: bool = False,
) -> str:
    """Generate text with proper system/user separation, **always using Gemini**.

    Even if callers pass an OpenAI-style model name, this router will send the
    request to the Gemini provider so the whole system runs on a single stack.
    """
    resolved = (model or CHAT_MODEL or DEFAULT_MODEL_NO_TOKENS).strip() or DEFAULT_MODEL_NO_TOKENS

    # If GOOGLE_API_KEY is missing, surface a clear error instead of silently
    # trying to hit OpenAI.
    if not GOOGLE_API_KEY:
        _log.error("GOOGLE_API_KEY is not set — Gemini is required as the sole provider.")
        return "Error: GOOGLE_API_KEY is not set (Gemini provider is required)."

    return _gemini.generate(
        user_prompt,
        system_prompt=system_prompt,
        # If a Gemini model name is provided, respect it; otherwise use default.
        model=resolved if _is_gemini(resolved) else None,
        max_tokens=max_tokens,
        json_mode=json_mode,
    )


def embed(text: str, model: str | None = None) -> list[float]:
    """Return an embedding vector via Gemini. Results are cached in Redis."""
    from app.config import GOOGLE_API_KEY

    if not GOOGLE_API_KEY:
        _log.warning("GOOGLE_API_KEY not set — cannot embed")
        return []

    from app.cache import cache_get, cache_set, NS_EMBEDDING, TTL_EMBEDDING

    cached = cache_get(NS_EMBEDDING, text, model)
    if cached is not None:
        _log.debug("embed cache HIT (len=%d)", len(cached))
        return cached

    result = _gemini.embed(text, model=model)

    if result:
        cache_set(NS_EMBEDDING, text, model, value=result, ttl=TTL_EMBEDDING)

    return result
