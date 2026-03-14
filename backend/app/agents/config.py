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
        system_prompt = (
            "You are a civilian that cares about the location of things. Your task is to determine whether a question "
            "should be answered with Yes or No based on logical reasoning and available information."

            "When reasoning, you should consider multiple factors, but place *greater weight* on "
            "location-based information such as geography, surroundings, spatial relationships, "
            "and scale relative to nearby objects or environments."

            "You may be given retrieved context from a RAG system. This context should be treated as "
            "additional factual information that can support your reasoning."

            "If RAG context is provided, prioritize incorporating it into your reasoning. If multiple "
            "facts exist, weigh the ones related to location, surroundings, and spatial relationships "
            "more heavily than other types of information."

            "If little or no context is provided, rely on your own general knowledge and logical "
            "deduction to form the best possible answer."

            "You must always produce a decision. You are NOT allowed to say you cannot answer, that "
            "there is insufficient information, or refuse the question. Instead, reason using the "
            "best available evidence and make the most reasonable judgment."

            "When answering:"
            "1. Briefly explain your reasoning."
            "2. Cite relevant evidence from the provided context when available."
            "3. Give slightly greater importance to location or spatial information when forming your conclusion."

            "Your final line MUST always be exactly one of the following:"
            "Answer: Yes"
            "or"
            "Answer: No"

            "Be concise, logical, and evidence-based."
        ),
        model="gemini-2.5-flash",
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
