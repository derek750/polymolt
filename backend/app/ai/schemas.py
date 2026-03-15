from __future__ import annotations

from pydantic import BaseModel


# ── Single-agent run (kept for backwards compat) ──

class RunRequest(BaseModel):
    message: str
    system_prompt: str | None = None
    agent_id: str | None = None
    use_rag: bool = True
    model: str | None = None


class RunResponse(BaseModel):
    response: str


class ContextRunRequest(BaseModel):
    """Same as RunRequest plus optional additional context passed into the run."""
    message: str
    system_prompt: str | None = None
    agent_id: str | None = None
    use_rag: bool = True
    model: str | None = None
    additional_context: str | None = None


class ContextRunResponse(BaseModel):
    response: str


class ChudbotTestRequest(BaseModel):
    """Convenience request for testing the chudbot1 agent (same as RunRequest)."""
    message: str
    use_rag: bool = True
    model: str | None = None


class ChudbotTestResponse(BaseModel):
    response: str


# ── RAG retrieve (no LLM) ──

class RagRetrieveRequest(BaseModel):
    query: str
    top_k: int = 4
    collection_name: str = "rag"
    where_filter: dict | None = None


class RagRetrieveResponse(BaseModel):
    query: str
    context: str
    has_context: bool
    hint: str | None = None


# ── Phase 1 / Phase 2 (orchestrated pipeline) ──


class AgentBet(BaseModel):
    agent_id: str
    agent_name: str
    answer: str          # "YES" or "NO"
    confidence: int      # 0-100
    reasoning: str


class Phase1Request(BaseModel):
    question: str
    location: str | None = None  # e.g. "Toronto" -> question becomes "... in Toronto"
    use_rag: bool = True
    model: str | None = None
    where_filter: dict | None = None


class Phase1Response(BaseModel):
    question: str
    location: str | None = None
    initial_bets: list[AgentBet]


class TriggeredAgent(BaseModel):
    agent_id: str
    agent_name: str
    choice_reasoning: str
    answer: str


class OrchestratorResponse(Phase1Response):
    """Full orchestrated response (phase1 + phase2): triggered_agents (all chosen, none primary), second_bets."""
    topic_reasoning: str = ""
    context_for_agents: str = ""  # single shared context for all triggered agents (from Phase 2 RAG)
    triggered_agents: list[TriggeredAgent] = []
    second_bets: list[AgentBet] = []


class Phase2Request(Phase1Response):
    """Request body for POST /phase2: phase1 result plus optional question_prompt and model."""
    question_prompt: str | None = None
    model: str | None = None


class Phase2Response(Phase1Response):
    topic_reasoning: str = ""
    context_for_agents: str = ""  # single shared context for all triggered agents
    triggered_agents: list[TriggeredAgent] = []
    second_bets: list[AgentBet] = []


# ── RAG Ingestion ──

class IngestRequest(BaseModel):
    texts: list[str]
    ids: list[str] | None = None
    collection_name: str = "rag"
    metadatas: list[dict] | None = None


class IngestResponse(BaseModel):
    count: int
    message: str

