"""Google Gemini provider — chat generation."""

from __future__ import annotations

import logging

from app.config import GOOGLE_API_KEY

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-1.5-flash"


def generate(
    user_prompt: str,
    *,
    system_prompt: str | None = None,
    model: str | None = None,
    max_tokens: int = 1024,
) -> str:
    """Call Gemini with optional system_instruction and return the text response."""
    model_name = (model or DEFAULT_MODEL).strip()
    if not GOOGLE_API_KEY:
        return "Error: GOOGLE_API_KEY is not set."
    try:
        import google.generativeai as genai
        genai.configure(api_key=GOOGLE_API_KEY)
        
        kwargs: dict = {}
        if system_prompt:
            kwargs["system_instruction"] = system_prompt
        
        agent = genai.GenerativeModel(model_name, **kwargs)
        resp = agent.generate_content(
            user_prompt,
            generation_config=genai.types.GenerationConfig(max_output_tokens=max_tokens)
        )
        return (resp.text or "").strip()
    except Exception as e:
        logger.exception("Gemini generate failed")
        return f"Error: {e!s}"


def embed(text: str, model: str | None = None) -> list[float]:
    """Return an embedding vector for *text* using Gemini, or [] on failure."""
    model_name = (model or "models/embedding-001").strip()
    if not GOOGLE_API_KEY:
        return []
    try:
        import google.generativeai as genai
        genai.configure(api_key=GOOGLE_API_KEY)
        result = genai.embed_content(model=model_name, content=text, task_type="retrieval_document")
        return result["embedding"]
    except Exception as e:
        logger.warning("Gemini embed failed: %s", e)
        return []
