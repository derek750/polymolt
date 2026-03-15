"""OpenAI provider — chat completions and embeddings."""

from __future__ import annotations

import logging

from app.config import OPENAI_API_KEY, OPENAI_BASE_URL, CHAT_MODEL, DEFAULT_MODEL_NO_TOKENS, EMBED_MODEL

logger = logging.getLogger(__name__)


def generate(
    user_prompt: str,
    *,
    system_prompt: str | None = None,
    model: str | None = None,
    max_tokens: int = 1024,
) -> str:
    """Call OpenAI chat completions with proper system/user roles."""
    model = (model or CHAT_MODEL or DEFAULT_MODEL_NO_TOKENS).strip() or DEFAULT_MODEL_NO_TOKENS
    if not OPENAI_API_KEY:
        return "Error: OPENAI_API_KEY is not set."
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL if OPENAI_BASE_URL else None
        )
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})
        r = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
        )
        return (r.choices[0].message.content or "").strip()
    except Exception as e:
        logger.exception("OpenAI generate failed")
        return f"Error: {e!s}"


def embed(text: str, model: str | None = None) -> list[float]:
    """Return an embedding vector for *text*, or [] on failure."""
    model = (model or EMBED_MODEL).strip()
    if not OPENAI_API_KEY:
        return []
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL if OPENAI_BASE_URL else None
        )
        r = client.embeddings.create(input=[text], model=model)
        return r.data[0].embedding
    except Exception as e:
        logger.warning("OpenAI embed failed: %s", e)
        return []
