"""Google Gemini provider — chat generation and embeddings (uses google.genai)."""

from __future__ import annotations

import logging

from app.config import GOOGLE_API_KEY

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-flash-latest"
DEFAULT_EMBED_MODEL = "models/gemini-embedding-001"


def generate(
    user_prompt: str,
    *,
    system_prompt: str | None = None,
    model: str | None = None,
    max_tokens: int = 1024,
    json_mode: bool = False,
) -> str:
    """Call Gemini with optional system_instruction and return the text response."""
    model_name = (model or DEFAULT_MODEL).strip()
    if not GOOGLE_API_KEY:
        return "Error: GOOGLE_API_KEY is not set."
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=GOOGLE_API_KEY)
        config_kwargs: dict = {"max_output_tokens": max_tokens}
        if system_prompt:
            config_kwargs["system_instruction"] = system_prompt
        if json_mode:
            config_kwargs["response_mime_type"] = "application/json"

        response = client.models.generate_content(
            model=model_name,
            contents=user_prompt,
            config=types.GenerateContentConfig(**config_kwargs),
        )
        return (response.text or "").strip()
    except Exception as e:
        logger.exception("Gemini generate failed")
        return f"Error: {e!s}"


def embed(text: str, model: str | None = None) -> list[float]:
    """Return an embedding vector for *text* using Gemini, or [] on failure."""
    model_name = (model or DEFAULT_EMBED_MODEL).strip()
    if not GOOGLE_API_KEY:
        return []
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=GOOGLE_API_KEY)
        result = client.models.embed_content(
            model=model_name,
            contents=text,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
        )
        if not result.embeddings:
            return []
        return list(result.embeddings[0].values)
    except Exception as e:
        logger.warning("Gemini embed failed: %s", e)
        return []
