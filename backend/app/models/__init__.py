"""
Centralized AI model access.

Usage:
    from app.models import generate, embed

generate() auto-routes to the correct provider based on the model name.
embed() currently uses OpenAI only (Gemini embeddings can be added later).
"""

from __future__ import annotations

from app.config import CHAT_MODEL
from app.models import openai as _openai
from app.models import gemini as _gemini


def _is_gemini(model: str) -> bool:
    return model.strip().lower().startswith("gemini")


def generate(
    user_prompt: str,
    *,
    system_prompt: str | None = None,
    model: str | None = None,
    max_tokens: int = 1024,
) -> str:
    """Generate text with proper system/user separation, routed by model name."""
    resolved = (model or CHAT_MODEL).strip()
    if _is_gemini(resolved):
        return _gemini.generate(
            user_prompt, system_prompt=system_prompt, model=resolved, max_tokens=max_tokens,
        )
    return _openai.generate(
        user_prompt, system_prompt=system_prompt, model=resolved, max_tokens=max_tokens,
    )


def embed(text: str, model: str | None = None) -> list[float]:
    """Return an embedding vector, routed by available key or model name."""
    from app.config import OPENAI_API_KEY
    resolved = (model or "").strip().lower()
    
    # If explicit Gemini model or no OpenAI key, use Gemini
    if resolved.startswith("models/") or not OPENAI_API_KEY:
        return _gemini.embed(text, model=model)
    
    return _openai.embed(text, model=model)
