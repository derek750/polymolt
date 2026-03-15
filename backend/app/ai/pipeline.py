"""
Run the RAG + specialized system-prompt agent pipeline.
Route calls this; returns the model response.
"""

from __future__ import annotations

import logging

from app.config import CHAT_MODEL, CHAT_MAX_TOKENS, DEFAULT_MODEL_NO_TOKENS, OPENAI_API_KEY
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
    if model_override and model_override.strip():
        return model_override.strip()
    if agent_id:
        agent = get_agent(agent_id)
        if agent and agent.model and agent.model.strip():
            return agent.model.strip()
    return (CHAT_MODEL or DEFAULT_MODEL_NO_TOKENS).strip() or DEFAULT_MODEL_NO_TOKENS


def run_pipeline(
    message: str,
    system_prompt: str | None = None,
    agent_id: str | None = None,
    use_rag: bool = True,
    model: str | None = None,
    additional_context: str | None = None,
    collection_name: str | None = None,
) -> str:
    """
    Run the pipeline: optional RAG retrieval + optional additional context + prompt → LLM → response.
    """
    if use_rag and not OPENAI_API_KEY:
        return "Error: OPENAI_API_KEY required for RAG (embeddings)."

    system = _resolve_system_prompt(system_prompt, agent_id)
    chat_model = _resolve_model(model, agent_id)
    
    # Default: orchestrator (no agent_id) uses 'rag' (deprecated) or provided name.
    # Agents (with agent_id) use 'sample_rag' unless overridden.
    if collection_name is None:
        collection_name = "sample_rag" if agent_id else "news_rag"

    rag_context = retrieve(message, top_k=4, collection_name=collection_name) if use_rag else ""

    context_parts: list[str] = []
    if rag_context:
        context_parts.append(f"Context (from RAG):\n{rag_context}")
    if additional_context:
        context_parts.append(f"Additional context:\n{additional_context}")

    context_block = "\n\n".join(context_parts) + "\n\n" if context_parts else ""
    user_content = f"{context_block}{message}"
    return generate(user_content, system_prompt=system, model=chat_model, max_tokens=CHAT_MAX_TOKENS)
