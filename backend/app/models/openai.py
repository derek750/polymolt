"""OpenAI provider — chat completions only.

Embeddings are handled by the Gemini provider; the OpenAI-compatible
proxy (HuggingFace Inference Endpoints) does not expose /embeddings.
"""

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
    json_mode: bool = False,
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
        kwargs: dict = {"model": model, "messages": messages, "max_tokens": max_tokens}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        r = client.chat.completions.create(**kwargs)
        return (r.choices[0].message.content or "").strip()
    except Exception as e:
        logger.exception("OpenAI generate failed")
        return f"Error: {e!s}"
