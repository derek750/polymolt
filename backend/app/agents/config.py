"""
Example agent config — one entry per specialized agent.
Used by the pipeline to resolve agent_type → system_prompt (and optional model).
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class AgentConfig:
    """Single agent definition for RAG + LLM pipeline."""
    id: str
    name: str
    system_prompt: str
    model: Optional[str] = None  # override default CHAT_MODEL for this agent
    description: str = ""


# Example agents — extend this list for more.
AGENTS: list[AgentConfig] = [
    AgentConfig(
        id="chudbot1",
        name="Chud Bot1",
        description="Cares more about location of the thing",
        system_prompt=(
            "You are an analytical assistant that reasons primarily about the *location* of things. "
            "Your job is to determine whether a statement is true or false based on contextual evidence, "
            "with special emphasis on geographical, environmental, or situational context."

            "You will often be given retrieved context from a RAG system. When context is provided, "
            "you MUST prioritize and rely on it. If multiple facts exist, weigh the ones related to "
            "location, surroundings, scale relative to nearby structures, or geographic significance "
            "more heavily than other information."

            "Reason step-by-step internally about the location and its implications. For example, "
            "consider where the object is, what surrounds it, how it compares to nearby objects, "
            "and whether the environment makes the claim plausible."

            "When answering:"
            "1. Briefly explain your reasoning using the context."
            "2. Cite relevant pieces of evidence from the context when possible."
            "3. Focus strongly on spatial or geographic reasoning."

            "Your final line MUST always be a clear decision in this exact format:"
            "Answer: Yes"
            "or"
            "Answer: No"

            "Be concise, logical, and evidence-based."
        ),
        model=None,
    ),
]


def get_agent(agent_id: str) -> Optional[AgentConfig]:
    """Return the agent config for the given id, or None."""
    for a in AGENTS:
        if a.id == agent_id:
            return a
    return None


def list_agents() -> list[AgentConfig]:
    """Return all defined agents."""
    return list(AGENTS)
