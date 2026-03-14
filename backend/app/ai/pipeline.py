"""
Run the RAG + specialized system-prompt agent pipeline.
Route calls this; returns the model response.
"""

from __future__ import annotations

import logging

from app.config import CHAT_MODEL, CHAT_MAX_TOKENS, OPENAI_API_KEY
from app.models import generate
from app.ai.rag import retrieve
from app.agents.config import get_agent

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "You are a climate and sustainability analyst. "
    "Answer only using the provided context when available. Be concise."
)


def _resolve_system_prompt(system_prompt: str | None, agent_id: str | None) -> str:
    if system_prompt:
        return system_prompt.strip()
    if agent_id:
        agent = get_agent(agent_id)
        if agent:
            return agent.system_prompt
    return DEFAULT_SYSTEM_PROMPT


def _resolve_model(model_override: str | None, agent_id: str | None) -> str:
    if model_override:
        return model_override.strip()
    if agent_id:
        agent = get_agent(agent_id)
        if agent and agent.model:
            return agent.model
    return CHAT_MODEL


def run_pipeline(
    message: str,
    system_prompt: str | None = None,
    agent_id: str | None = None,
    use_rag: bool = True,
    model: str | None = None,
) -> str:
    """
    Run the pipeline: optional RAG retrieval + prompt (system + context + message) → LLM → response.
    """
    if use_rag and not OPENAI_API_KEY:
        return "Error: OPENAI_API_KEY required for RAG (embeddings)."

    system = _resolve_system_prompt(system_prompt, agent_id)
    chat_model = _resolve_model(model, agent_id)
    context = retrieve(message, top_k=4) if use_rag else ""
    if context:
        context_block = f"Context (from RAG):\n{context}\n\n"
    else:
        context_block = ""

    user_content = f"{context_block}{message}"
    return generate(user_content, system_prompt=system, model=chat_model, max_tokens=CHAT_MAX_TOKENS)
