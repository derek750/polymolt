"""
Run the RAG + specialized system-prompt agent pipeline.
Route calls this; returns the model response.
"""

from __future__ import annotations

import logging

from app.config import CHAT_MODEL, OPENAI_API_KEY, GOOGLE_API_KEY
from app.rag import retrieve
from app.agents.config import get_agent

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "You are a climate and sustainability analyst. "
    "Answer only using the provided context when available. Be concise."
)


def _resolve_system_prompt(system_prompt: str | None, agent_type: str | None) -> str:
    if system_prompt:
        return system_prompt.strip()
    if agent_type:
        agent = get_agent(agent_type)
        if agent:
            return agent.system_prompt
    return DEFAULT_SYSTEM_PROMPT


def _resolve_model(model_override: str | None, agent_type: str | None) -> str:
    if model_override:
        return model_override.strip()
    if agent_type:
        agent = get_agent(agent_type)
        if agent and agent.model:
            return agent.model
    return CHAT_MODEL


def _is_gemini_model(model: str) -> bool:
    """True if model is a Gemini model (use Google API)."""
    return model.strip().lower().startswith("gemini-")


def run_pipeline(
    message: str,
    system_prompt: str | None = None,
    agent_type: str | None = None,
    use_rag: bool = True,
    model: str | None = None,
) -> str:
    """
    Run the pipeline: optional RAG retrieval + prompt (system + context + message) → LLM → response.
    Use agent_type to pick a predefined system prompt, or pass system_prompt to override.
    Use model to override (e.g. gpt-4o, gemini-1.5-flash). Gemini models call Google API.
    """
    if use_rag and not OPENAI_API_KEY:
        return "Error: OPENAI_API_KEY required for RAG (embeddings)."

    system = _resolve_system_prompt(system_prompt, agent_type)
    chat_model = _resolve_model(model, agent_type)
    context = retrieve(message, top_k=4) if use_rag else ""
    if context:
        context_block = f"\n\nContext (from RAG):\n{context}\n"
    else:
        context_block = "\n\n(No RAG context loaded.)\n"

    prompt = f"{system}{context_block}\n\nUser: {message}"

    if _is_gemini_model(chat_model):
        if not GOOGLE_API_KEY:
            return "Error: GOOGLE_API_KEY required for Gemini models."
        try:
            import google.generativeai as genai
            genai.configure(api_key=GOOGLE_API_KEY)
            gen_model = genai.GenerativeModel(chat_model)
            response = gen_model.generate_content(prompt)
            if response.text:
                return response.text.strip()
            return "Error: No text in Gemini response."
        except Exception as e:
            logger.exception("Pipeline Gemini call failed")
            return f"Error: {e!s}"
    else:
        if not OPENAI_API_KEY:
            return "Error: OPENAI_API_KEY required for OpenAI models."
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            r = client.chat.completions.create(
                model=chat_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
            )
            return (r.choices[0].message.content or "").strip()
        except Exception as e:
            logger.exception("Pipeline LLM call failed")
            return f"Error: {e!s}"
