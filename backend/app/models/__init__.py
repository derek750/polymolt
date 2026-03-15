"""
Centralized AI model access.

Usage:
    from app.models import generate, embed

generate() defaults to OpenAI (or compatible proxy) unless the model name
starts with "gemini", in which case it routes to the Gemini provider.

embed() always uses Gemini — the OpenAI-compatible proxy (HuggingFace
Inference Endpoints) does not expose an /embeddings route.
"""

from __future__ import annotations

from app.config import CHAT_MODEL, DEFAULT_MODEL_NO_TOKENS
from app.models import openai as _openai
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
    """Generate text with proper system/user separation, routed by model name."""
    resolved = (model or CHAT_MODEL or DEFAULT_MODEL_NO_TOKENS).strip() or DEFAULT_MODEL_NO_TOKENS
    if _is_gemini(resolved):
        return _gemini.generate(
            user_prompt, system_prompt=system_prompt, model=resolved, max_tokens=max_tokens, json_mode=json_mode,
        )
    return _openai.generate(
        user_prompt, system_prompt=system_prompt, model=resolved, max_tokens=max_tokens, json_mode=json_mode,
    )


def embed(text: str, model: str | None = None) -> list[float]:
    """Return an embedding vector via Gemini."""
    from app.config import GOOGLE_API_KEY

    if not GOOGLE_API_KEY:
        _log.warning("GOOGLE_API_KEY not set — cannot embed")
        return []
    return _gemini.embed(text, model=model)
